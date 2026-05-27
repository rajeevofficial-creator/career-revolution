"""
ApplyOrchestrator — State machine for job application navigation.

Replaces the monolithic _universal_interaction_loop with explicit
named states and clean transitions. Each state knows what to do and
what recovery means when it fails.

State flow:
  NAVIGATE → DISMISS_OVERLAYS → ANALYSE_PAGE →
    ├── JOB_DESCRIPTION  → FIND_APPLY_BUTTON → CLICK_APPLY →
    │                                               ↓
    ├── LOGIN_REQUIRED   → FILL_LOGIN         → ANALYSE_PAGE
    │
    ├── REGISTER         → FILL_REGISTER      → ANALYSE_PAGE
    │
    ├── FORM_STEP        → FILL_FORM_STEP ────→ ANALYSE_PAGE (loop)
    │
    ├── REVIEW           → SUBMIT_APPLICATION →
    │
    ├── SUCCESS          → VERIFY_SUCCESS     → DONE ✓
    │
    └── CAPTCHA/STUCK    → INTERVENTION        → (wait for user)

LLM budget per application (typical):
  - Page analyses:    2–4 × MICRO (DOM-rich pages)
  - Form steps:       2–4 × MICRO (one survey per step)
  - Vision fallback:  0–2 × VISION (only for ambiguous pages)
  Total Gemini Flash cost: ~$0.001 per application
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import Any, Dict, List, Optional

from agents.core.base_agent import BaseAgent
from agents.core.llm_bridge import LLMTier
from agents.apply_engine.page_analyst import PageAnalyst, PageState, PageAnalysis
from agents.apply_engine.form_filler import FormFiller, _human_delay

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Result
# ─────────────────────────────────────────────────────────────────────────────

class ApplyResult:
    def __init__(
        self,
        success: bool,
        intervention: bool,
        message: str,
        log: List[str],
        new_account: Optional[Dict] = None,
    ):
        self.success = success
        self.intervention = intervention
        self.message = message
        self.log = log
        self.new_account = new_account

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "intervention": self.intervention,
            "message": self.message,
            "log": self.log,
            "new_account": self.new_account,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Overlay dismissal selectors (ordered by priority)
# ─────────────────────────────────────────────────────────────────────────────

_OVERLAY_SELECTORS = [
    'button:has-text("Accept all")',
    'button:has-text("Accept")',
    'button:has-text("Agree")',
    'button:has-text("Akzeptieren")',
    'button:has-text("Tout accepter")',
    'button[aria-label="Dismiss"]',
    'button[aria-label="Close"]',
    'button[aria-label="Close modal"]',
    '.artdeco-modal__dismiss',
    '.modal__close',
    '.privacy-policy-banner__dismiss',
    'button:has-text("Reject all")',
    'button:has-text("Ablehnen")',
    'button:has-text("Maybe later")',
    'button:has-text("Not now")',
    '.artdeco-toast-item__dismiss',
    'button[data-test-modal-close-btn]',
]

# Selectors that are safe to infer as success without text analysis
_SUCCESS_SELECTORS = [
    'h2:has-text("Application submitted")',
    'h3:has-text("Your application was sent")',
    'h2:has-text("applied")',
    '.artdeco-toast-item--success',
    '[data-test-modal-id="post-apply-modal"]',
    'h1:has-text("Thank you")',
    'h2:has-text("Thank you")',
    'p:has-text("application has been submitted")',
    'p:has-text("successfully applied")',
]


# ─────────────────────────────────────────────────────────────────────────────
# ApplyOrchestrator
# ─────────────────────────────────────────────────────────────────────────────

class ApplyOrchestrator(BaseAgent):
    """
    Top-level apply agent. Takes a Playwright page and user profile dict,
    navigates and fills the application to completion or intervention.

    Usage:
        orch = ApplyOrchestrator()
        result = await orch.run(page, app_data)
    """

    MAX_STEPS = 30
    MAX_SAME_STATE_REPEATS = 3

    def __init__(self, provider: Optional[str] = None):
        super().__init__(provider=provider)
        self._analyst = PageAnalyst(llm=self.llm)
        self._filler  = FormFiller(llm=self.llm)

    async def run(self, page, app_data: Dict[str, Any]) -> ApplyResult:
        """
        Main entry point. Navigates from the job URL to a confirmed
        submitted state (or intervention).
        """
        log: List[str] = []
        url = app_data.get("url", "")

        if not url:
            return ApplyResult(False, True, "No application URL provided.", log)

        log.append(f"ApplyOrchestrator: starting for {url}")

        # ── Navigate to the job page ──────────────────────────────────────────
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            await _human_delay(1500, 3000)
        except Exception as e:
            log.append(f"Navigation error: {e}")
            return ApplyResult(False, True, f"Could not navigate to {url}: {e}", log)

        # ── Handle LinkedIn safety redirect immediately ────────────────────────
        # linkedin.com/safety/go/ is shown when navigating to an external link.
        # Click "Continue" to pass through, then re-navigate if needed.
        await self._handle_linkedin_safety_redirect(page, url, log)

        # ── State machine loop ────────────────────────────────────────────────
        prev_state: Optional[PageState] = None
        same_state_count = 0
        new_account: Optional[Dict] = None

        for step in range(self.MAX_STEPS):
            log.append(f"\n── Step {step + 1} ─────────────────────────────")

            # ── Tab / Popup management ────────────────────────────────────────
            try:
                if page.is_closed():
                    log.append("Current tab was closed. Switching back to an active tab.")
                    pages = page.context.pages
                    active_pages = [p for p in pages if not p.is_closed() and (p.url.startswith("http") or p.url == "about:blank")]
                    if active_pages:
                        page = active_pages[0]
                        log.append(f"Switched to active tab: {page.url}")
                    else:
                        return ApplyResult(False, True, "All browser tabs were closed.", log, new_account)
            except Exception as e:
                log.append(f"Tab check error: {e}")

            try:
                pages = page.context.pages
                if len(pages) > 1:
                    active_pages = [p for p in pages if not p.is_closed() and (p.url.startswith("http") or p.url == "about:blank")]
                    if active_pages and active_pages[-1] != page:
                        new_page = active_pages[-1]
                        log.append(f"Detecting new tab/popup. Switching context to: {new_page.url}")
                        page = new_page
                        # Allow some time to load
                        await _human_delay(1500, 3000)
            except Exception as e:
                log.append(f"New tab check error: {e}")

            # Always try to clear overlays first (free, no LLM)
            dismissed = await self._dismiss_overlays(page, log)
            if dismissed:
                await _human_delay(800, 1500)

            # Handle LinkedIn safety redirect immediately (free, no LLM)
            current_url = page.url
            if "linkedin.com/safety" in current_url or "safety/go" in current_url:
                await self._handle_linkedin_safety_redirect(page, current_url, log)
                await _human_delay(1000, 2000)
                continue

            # Detect dead-end pages before LLM call (free)
            current_url = page.url
            page_title = await page.title()
            if any(kw in page_title.lower() for kw in ("page not found", "not found", "404", "error")):
                log.append(f"Page not found: '{page_title}' at {current_url}")
                return ApplyResult(
                    False, True,
                    f"The job page could not be found ('{page_title}'). "
                    "The listing may have expired or the URL is incorrect.",
                    log, new_account,
                )

            # Quick DOM success check before LLM call
            if await self._check_success(page):
                log.append("Success indicators detected before analysis.")
                return ApplyResult(True, False, "Application submitted successfully.", log, new_account)

            # Analyse current page
            try:
                analysis = await self._analyst.analyse(page)
            except Exception as e:
                log.append(f"Page analysis error: {e}")
                analysis = None

            if not analysis:
                log.append("Could not analyse page — requesting intervention.")
                return ApplyResult(False, True, "Page analysis failed. Please complete manually.", log, new_account)

            log.append(f"Page state: {analysis.state.value} | step='{analysis.step_label}' | conf={analysis.confidence}%")

            # Stuck detection
            if analysis.state == prev_state:
                same_state_count += 1
                if same_state_count >= self.MAX_SAME_STATE_REPEATS:
                    log.append(f"Stuck in state {analysis.state.value} for {same_state_count} iterations.")
                    return ApplyResult(
                        False, True,
                        f"Agent is stuck on '{analysis.step_label or analysis.state.value}'. "
                        "Please check the browser window and complete any required fields, then resume.",
                        log, new_account,
                    )
            else:
                same_state_count = 0
            prev_state = analysis.state

            # ── Dispatch on state ─────────────────────────────────────────────
            result = await self._dispatch(page, analysis, app_data, log)

            if result == "CONTINUE":
                continue
            elif result == "SUCCESS":
                return ApplyResult(True, False, "Application submitted successfully.", log, new_account)
            elif result == "INTERVENTION":
                msg = log[-1] if log else "Intervention required."
                return ApplyResult(False, True, msg, log, new_account)
            # "LOOP" → just continue the loop

        return ApplyResult(
            False, True,
            "Maximum steps reached without confirmation. Please check and complete manually.",
            log, new_account,
        )

    # ── State dispatcher ──────────────────────────────────────────────────────

    async def _dispatch(
        self,
        page,
        analysis: PageAnalysis,
        app_data: Dict[str, Any],
        log: List[str],
    ) -> str:
        """
        Handle the current page state.
        Returns: "CONTINUE" | "SUCCESS" | "INTERVENTION" | "LOOP"
        """
        state = analysis.state

        if state == PageState.LOADING:
            log.append("Page still loading — waiting...")
            await _human_delay(2000, 4000)
            return "CONTINUE"

        if state == PageState.OVERLAY:
            # Extra overlay pass (analyst saw one we may have missed)
            await self._dismiss_overlays(page, log)
            await _human_delay(800, 1500)
            return "CONTINUE"

        if state == PageState.SUCCESS:
            log.append("Success page confirmed by analyst.")
            return "SUCCESS"

        if state == PageState.CAPTCHA:
            log.append("CAPTCHA detected — human intervention required.")
            return "INTERVENTION"

        if state == PageState.EMAIL_VERIFY:
            log.append("Email verification required. Please verify your email then click Resume.")
            return "INTERVENTION"

        if state in (PageState.LOGIN, PageState.REGISTER):
            return await self._handle_auth(page, analysis, app_data, log)

        if state == PageState.JOB_DESCRIPTION:
            return await self._click_apply_button(page, analysis, app_data, log)

        if state in (PageState.FORM_STEP, PageState.REVIEW):
            return await self._handle_form_step(page, analysis, app_data, log)

        if state == PageState.REDIRECT:
            # Handle safety/redirect pages — try to pass through, don't loop
            current_url = page.url
            log.append(f"Redirect page detected: {current_url}")
            await self._handle_linkedin_safety_redirect(page, current_url, log)
            # After handling, wait for final destination
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await _human_delay(1500, 3000)
            except Exception:
                pass
            # If we're still on a safety/redirect page after handling, give up
            if "safety/go" in page.url or "linkedin.com/safety" in page.url:
                log.append("Still on LinkedIn safety page after bypass attempt.")
                return "INTERVENTION"
            return "CONTINUE"

        # UNKNOWN — check for 404 / page-not-found before attempting form fill
        current_url = page.url
        if any(kw in current_url.lower() for kw in ("safety/go", "404", "not-found", "error")):
            log.append(f"Page appears to be an error/redirect page: {current_url}")
            return "INTERVENTION"

        log.append(f"Unknown page state — attempting generic form fill.")
        return await self._handle_form_step(page, analysis, app_data, log)

    # ── Auth handler ──────────────────────────────────────────────────────────

    async def _handle_auth(
        self,
        page,
        analysis: PageAnalysis,
        app_data: Dict[str, Any],
        log: List[str],
    ) -> str:
        log.append(f"Auth state: {analysis.state.value}")
        result = await self._filler.fill_step(page, analysis, app_data, log)
        if not result.get("navigated"):
            # Try clicking submit manually
            for sel in ['button[type="submit"]', 'button:has-text("Sign in")', 'button:has-text("Log in")', 'input[type="submit"]']:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    log.append(f"Auth: clicked submit via fallback selector: {sel}")
                    break

        await _human_delay(2000, 4000)

        # Check for checkpoint / 2FA
        current = page.url.lower()
        if any(kw in current for kw in ("checkpoint", "challenge", "verify", "two-step")):
            log.append("Login requires 2FA/checkpoint verification.")
            return "INTERVENTION"

        return "CONTINUE"

    # ── Apply button handler ──────────────────────────────────────────────────

    async def _click_apply_button(
        self,
        page,
        analysis: PageAnalysis,
        app_data: Dict[str, Any],
        log: List[str],
    ) -> str:
        """Click the Apply / Easy Apply button on a job description page."""

        # Use analyst's identified button ID first
        apply_id = analysis.apply_button_id
        if apply_id:
            btn = await page.query_selector(f'[data-cr-id="{apply_id}"]')
            if btn and await btn.is_visible():
                log.append(f"Clicking apply button [{apply_id}] (analyst identified)")
                try:
                    await btn.click(force=True)
                except Exception:
                    await page.evaluate("el => el.click()", btn)
                await _human_delay(1000, 2000)
                return "CONTINUE"

        # Fallback: broad selector search
        candidates = await page.query_selector_all(
            'button.jobs-apply-button, a.jobs-apply-button, '
            'button[aria-label*="Apply"], a[aria-label*="Apply"], '
            'button:has-text("Easy Apply"), button:has-text("Apply"), '
            'a:has-text("Apply for this job"), a:has-text("Jetzt bewerben"), '
            'a:has-text("Postuler"), a[data-cy="apply-button"]'
        )
        for btn in candidates:
            if await btn.is_visible():
                aria = (await btn.get_attribute("aria-label") or "").lower()
                text = (await btn.inner_text()).strip()
                log.append(f"Apply candidate: aria='{aria}' text='{text}'")
                try:
                    await btn.scroll_into_view_if_needed()
                    await btn.click(force=True)
                    log.append(f"Clicked apply button: '{text}'")
                    await _human_delay(1000, 2000)
                    return "CONTINUE"
                except Exception as e:
                    log.append(f"Click failed: {e}")
                    continue

        log.append("No Apply button found — page may have expired or changed.")
        return "INTERVENTION"

    # ── Form step handler ─────────────────────────────────────────────────────

    async def _handle_form_step(
        self,
        page,
        analysis: PageAnalysis,
        app_data: Dict[str, Any],
        log: List[str],
    ) -> str:
        result = await self._filler.fill_step(page, analysis, app_data, log)

        if result.get("navigated"):
            await _human_delay(1200, 2500)
            # Check for immediate success
            if await self._check_success(page):
                return "SUCCESS"
            return "CONTINUE"

        # Navigation button was not found — try fallback selectors
        log.append("FormFiller did not navigate — trying fallback navigation.")
        for sel in [
            'button:has-text("Submit application")',
            'button:has-text("Submit")',
            'button:has-text("Review")',
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'button:has-text("Weiter")',
            'button:has-text("Suivant")',
        ]:
            btn = await page.query_selector(sel)
            if btn and await btn.is_visible():
                disabled = await btn.get_attribute("disabled")
                if disabled is not None:
                    log.append(f"Next/Submit button disabled — may have unfilled required fields.")
                    return "INTERVENTION"
                log.append(f"Fallback nav: clicking '{sel}'")
                try:
                    await btn.click(force=True)
                except Exception:
                    await page.evaluate("el => el.click()", btn)
                await _human_delay(1200, 2200)
                if await self._check_success(page):
                    return "SUCCESS"
                return "CONTINUE"

        # Nothing worked
        log.append("Could not advance form — no enabled navigation button found.")
        return "INTERVENTION"

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _handle_linkedin_safety_redirect(self, page, original_url: str, log: List[str]):
        """
        LinkedIn intercepts external links with a safety/warning page at:
          linkedin.com/safety/go/?_l=...
        This page has a 'Continue' or 'Proceed' button that must be clicked
        to reach the actual destination. If we're on this page, click through.
        """
        current_url = page.url
        if "linkedin.com/safety" not in current_url and "safety/go" not in current_url:
            return  # Not a safety page, nothing to do

        log.append(f"LinkedIn safety redirect detected: {current_url}")

        # Try clicking the continue button
        for sel in [
            'a:has-text("Continue")',
            'a:has-text("Proceed")',
            'button:has-text("Continue")',
            'a[href*="safety"]',
            '.main-content a',
            'a[class*="proceed"]',
            'a[class*="continue"]',
        ]:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    href = await el.get_attribute("href") or ""
                    text = (await el.inner_text()).strip()
                    log.append(f"Safety page: clicking '{text}' ({sel}) → {href[:80]}")
                    await el.click()
                    await _human_delay(1500, 2500)
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                    log.append(f"After safety bypass: {page.url}")
                    return
            except Exception:
                continue

        log.append("Safety page: no 'Continue' button found — page may require manual action.")

    async def _dismiss_overlays(self, page, log: List[str]) -> bool:
        dismissed = False
        for sel in _OVERLAY_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click(timeout=2000)
                    log.append(f"Dismissed overlay: {sel}")
                    dismissed = True
                    await asyncio.sleep(0.5)
            except Exception:
                pass
        return dismissed

    async def _check_success(self, page) -> bool:
        """DOM-only success check — zero LLM cost."""
        for sel in _SUCCESS_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    return True
            except Exception:
                pass
        return False
