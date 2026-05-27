"""
AutoApplyAgent — Human-like browser automation for job applications.

Supports:
  - LinkedIn Easy Apply
  - "Sign in with LinkedIn" portals
  - Common ATS platforms: Workday, Greenhouse, Lever, SuccessFactors, SmartRecruiters
  - Generic form-filler fallback

Key behaviours:
  - Human-like delays, randomized typing speed
  - Stealth headers to avoid bot detection
  - Feedback loop: sets JobApplication.status = 'requires_intervention'
    and populates intervention_message when it gets stuck
  - Tracks new accounts created during automation in AutoApplyAccount
  - Email verification: pauses & notifies user (manual verification)
  - Resumes after user provides intervention data via API
"""

import asyncio
import concurrent.futures
import json
import logging
import random
import re
import string
import os
import sys
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.database import (
    JobApplication,
    JobOpportunity,
    User,
    UserProfile,
    AutoApplyCredential,
    AutoApplyAccount,
    LinkedInSession,
)
from app.utils.security import decrypt_value
from app.services.llm_analysis import LLMAnalysisService
from app.services.email_verification import EmailVerificationService

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Human-like helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _human_delay(min_ms: int = 500, max_ms: int = 2500):
    """Random sleep between min and max milliseconds."""
    delay = random.uniform(min_ms / 1000, max_ms / 1000)
    await asyncio.sleep(delay)


async def _type_like_human(page, selector: str, text: str):
    """
    Click a field and type character-by-character with random delays
    to mimic human typing speed (60–120 WPM ≈ 40–100ms per char).
    """
    await page.click(selector)
    await _human_delay(100, 400)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.04, 0.12))


def _stealth_headers() -> dict:
    """Return realistic browser-like headers to avoid bot fingerprinting."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "DNT": "1",
    }


def _random_viewport() -> dict:
    """Return a realistic browser viewport size."""
    viewports = [
        {"width": 1920, "height": 1080},
        {"width": 1440, "height": 900},
        {"width": 1366, "height": 768},
        {"width": 1280, "height": 800},
    ]
    return random.choice(viewports)


def _generate_password(length: int = 14) -> str:
    """Generate a strong random password for new portal accounts."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choices(chars, k=length))


# ─────────────────────────────────────────────────────────────────────────────
# ATS Platform Detectors
# ─────────────────────────────────────────────────────────────────────────────

def _detect_ats(url: str) -> str:
    """Detect which ATS platform a URL belongs to."""
    url_lower = url.lower()
    if "linkedin.com" in url_lower:
        return "linkedin"
    if "workday.com" in url_lower or "myworkdayjobs.com" in url_lower:
        return "workday"
    if "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower:
        return "greenhouse"
    if "lever.co" in url_lower or "jobs.lever.co" in url_lower:
        return "lever"
    if "successfactors" in url_lower or "successfactors.eu" in url_lower:
        return "successfactors"
    if "smartrecruiters.com" in url_lower:
        return "smartrecruiters"
    if "taleo.net" in url_lower:
        return "taleo"
    if "icims.com" in url_lower:
        return "icims"
    if "jobs.ch" in url_lower:
        return "jobsch"
    return "generic"


# ─────────────────────────────────────────────────────────────────────────────
# Platform-Specific Strategies
# ─────────────────────────────────────────────────────────────────────────────

def _extract_linkedin_job_id(url: str) -> str | None:
    """Extract a LinkedIn job ID from any LinkedIn URL variant."""
    # /jobs/view/1234567890/
    m = re.search(r'/jobs/view/(\d+)', url)
    if m:
        return m.group(1)
    # ?currentJobId=1234567890
    m = re.search(r'[?&]currentJobId=(\d+)', url)
    if m:
        return m.group(1)
    # /jobs/search/?...&currentJobId= or easy-apply collections
    return None


def _normalize_linkedin_url(url: str) -> str:
    """
    Convert any LinkedIn job URL variant to a canonical /jobs/view/{id}/ URL.
    Supported variants:
      - /jobs/collections/recommended/?currentJobId=XXXXX
      - /jobs/collections/easy-apply/?currentJobId=XXXXX
      - /jobs/search/?currentJobId=XXXXX
      - /jobs/view/XXXXX/
    """
    job_id = _extract_linkedin_job_id(url)
    if job_id:
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    return url  # Already canonical or unknown format


_LABEL_ELEMENTS_JS = """
(function() {
    // Remove existing labels if any
    const existing = document.querySelectorAll('.cr-vision-label');
    existing.forEach(e => e.remove());

    const elements = document.querySelectorAll('button, a, input[type="submit"], input[type="button"]');
    let count = 0;
    
    elements.forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.top <= window.innerHeight) {
            count++;
            el.setAttribute('data-cr-id', count);
            
            const label = document.createElement('div');
            label.className = 'cr-vision-label';
            label.innerText = '[' + count + ']';
            label.style.position = 'absolute';
            label.style.top = (rect.top + window.scrollY) + 'px';
            label.style.left = (rect.left + window.scrollX) + 'px';
            label.style.backgroundColor = 'rgba(255, 0, 0, 0.8)';
            label.style.color = 'white';
            label.style.padding = '2px 5px';
            label.style.fontSize = '12px';
            label.style.fontWeight = 'bold';
            label.style.zIndex = '1000000';
            label.style.pointerEvents = 'none';
            label.style.borderRadius = '3px';
            document.body.appendChild(label);
        }
    });
    return count;
})();
"""

async def _identify_with_vision(page, goal: str, log: list) -> Optional[str]:
    """
    Use Gemini Vision to find an element when selectors fail.
    Returns the data-cr-id string or None.
    """
    try:
        log.append(f"Vision-Assisted Recovery: Identifying target for '{goal}'...")
        # 1. Label elements
        labeled_count = await page.evaluate(_LABEL_ELEMENTS_JS)
        log.append(f"Labeled {labeled_count} interactive elements.")
        await asyncio.sleep(0.5)
        
        # 2. Capture screenshot
        screenshot = await page.screenshot(type="png", full_page=False)
        
        # 3. Call LLM
        llm = LLMAnalysisService()
        result = await llm.identify_ui_element(screenshot, goal)
        
        # 4. Clean up labels
        await page.evaluate("document.querySelectorAll('.cr-vision-label').forEach(e => e.remove())")
        
        if result.get("element_id"):
            id_val = str(result["element_id"]).strip("[] ")
            log.append(f"Vision identified element [{id_val}]: {result.get('reasoning', '')}")
            return id_val
    except Exception as e:
        log.append(f"Vision recovery failed: {str(e)}")
    return None


async def _apply_linkedin(page, app_data: dict, creds: dict) -> dict:
    """
    LinkedIn apply flow supporting all URL variants and both Easy Apply
    and external-redirect Apply buttons.
    Returns {success, intervention, message, log}.
    """
    log = []
    try:
        # --- Step 1: Normalize URL to direct job view ---
        raw_url = app_data["url"]
        canonical_url = _normalize_linkedin_url(raw_url)
        if canonical_url != raw_url:
            log.append(f"Normalizing LinkedIn URL to: {canonical_url}")

        # --- Step 2: ALWAYS log in first before navigating to job ---
        # LinkedIn shows different buttons (Easy Apply vs Apply) depending on
        # login state. A fresh automation browser has no session cookies, so
        # we must authenticate before reaching the job page.
        if creds.get("linkedin_username") and creds.get("linkedin_password"):
            log.append("Logging into LinkedIn before navigating to job...")
            login_ok = await _linkedin_login(page, creds, log)
            if not login_ok:
                return {
                    "success": False,
                    "intervention": True,
                    "message": "LinkedIn login requires additional verification (2FA or checkpoint). Please log in manually in the open browser window, then click 'Resume Automation'.",
                    "log": log,
                }
        else:
            return {
                "success": False,
                "intervention": True,
                "message": "LinkedIn credentials are not configured. Please add your LinkedIn email and password in Auto-Application Settings.",
                "log": log,
            }

        # --- Step 3: Navigate to the job page (now authenticated) ---
        log.append(f"Navigating to job: {canonical_url}")
        await page.goto(canonical_url, wait_until="domcontentloaded", timeout=30000)

        # LinkedIn is a SPA — wait for JS to render the apply button before querying
        try:
            await page.wait_for_selector(
                'button[aria-label*="Apply"], .jobs-apply-button, button:has-text("Apply")',
                state="visible", timeout=12000
            )
        except Exception:
            log.append("Warning: Apply button did not appear within 12s, trying anyway...")
        await _human_delay(1500, 2500)

        # Check for cookie banner or "Sign in" prompt on the job page
        for overlay_sel in [
            'button:has-text("Accept")', # Cookie banner
            '.artdeco-modal__dismiss',   # Generic modal close
            'button[aria-label="Dismiss"]',
            'button[aria-label="Close"]',
            '.modal__overlay--visible button[class*="close"]'
        ]:
            overlay = await page.query_selector(overlay_sel)
            if overlay and await overlay.is_visible():
                log.append(f"Dismissing blocking overlay: {overlay_sel}")
                try: await overlay.click()
                except Exception: pass
                await _human_delay(500, 1000)

        # Verify we're still logged in - look for the 'Me' icon or global nav
        nav = await page.query_selector('.global-nav__me, [data-test-id="global-nav"]')
        if not nav:
            log.append("User session not detected on job page. Likely encountered a login wall.")
            # One more attempt to dismiss a sign-in modal if it's there
            signin_modal = await page.query_selector('.modal__overlay--visible, [data-test-id="auth-wall"]')
            if signin_modal:
                log.append("Sign-in wall detected. Automation cannot proceed without active session.")
                return {
                    "success": False, "intervention": True,
                    "message": "LinkedIn session was lost or blocked. Please log in manually and reconnect.",
                    "log": log
                }

        # --- Step 4: Identify button type using aria-label (most reliable on LinkedIn) ---
        # LinkedIn's Easy Apply button: aria-label="Easy Apply to [Title] at [Company]"
        # LinkedIn's external Apply button: aria-label="Apply to [Title] at [Company]"
        # We read the aria-label of every visible apply button and classify it.

        log.append(f"Searching for apply buttons with broad selectors...")
        all_apply_btns = await page.query_selector_all(
            'button.jobs-apply-button, a.jobs-apply-button, '
            'button[aria-label*="Apply"], a[aria-label*="Apply"], '
            'button:has-text("Apply"), a:has-text("Apply"), '
            'button:has-text("interested"), a:has-text("interested"), '
            'button:has-text("Easy Apply"), a:has-text("Easy Apply")'
        )
        log.append(f"Found {len(all_apply_btns)} potential candidates.")

        easy_apply_btn = None
        external_apply_btn = None

        for i, btn in enumerate(all_apply_btns):
            try:
                visible = await btn.is_visible()
                aria = (await btn.get_attribute("aria-label") or "").lower()
                text = (await btn.inner_text()).strip().lower()
                log.append(f"Candidate {i} (Visible={visible}): aria='{aria}' text='{text}'")
                
                if not visible:
                    continue

                if "easy apply" in aria or "easy apply" in text or "interested" in aria or "interested" in text:
                    easy_apply_btn = btn
                    log.append(f"Classified as EASY APPLY: Candidate {i}")
                    break
                elif "apply" in aria or "apply" in text:
                    if external_apply_btn is None:
                        external_apply_btn = btn
                        log.append(f"Classified as EXTERNAL APPLY: Candidate {i}")
            except Exception as e:
                log.append(f"Error checking candidate {i}: {str(e)}")
                continue

        if not easy_apply_btn and not external_apply_btn:
            log.append("No candidates matched keywords. TRIGGERING VISION...")
            vision_id = await _identify_with_vision(page, "Find the 'Apply', 'Easy Apply', or 'Interested' button/link to start the application.", log)
            if vision_id and vision_id != "null":
                target = await page.query_selector(f'[data-cr-id="{vision_id}"]')
                if target:
                    aria = (await target.get_attribute("aria-label") or "").lower()
                    text = (await target.inner_text()).strip().lower()
                    log.append(f"Vision target {vision_id} info: aria='{aria}' text='{text}'")
                    if "easy apply" in aria or "easy apply" in text or "interested" in aria or "interested" in text:
                        easy_apply_btn = target
                        log.append(f"Vision recovery matched: EASY APPLY (via ID {vision_id})")
                    else:
                        external_apply_btn = target
                        log.append(f"Vision recovery matched: EXTERNAL APPLY (via ID {vision_id})")
            else:
                log.append("Vision returned no target ID.")

        # --- Step 5: Act on button type ---
        if easy_apply_btn:
            log.append("Clicking Easy Apply button...")
            try:
                await easy_apply_btn.scroll_into_view_if_needed()
                await _human_delay(500, 1000)
                # Force click via JS for maximum reliability on SPA anchors
                await page.evaluate("el => el.click()", easy_apply_btn)
            except Exception as ce:
                log.append(f"Standard click failed ({ce}), trying force click...")
                await easy_apply_btn.click(force=True)

            # Wait for the Easy Apply modal to open before filling
            try:
                await page.wait_for_selector(
                    '.jobs-easy-apply-modal, [data-test-modal-id="easy-apply-modal"], '
                    '.artdeco-modal[role="dialog"], .top-level-modal-container, '
                    '.modal__overlay--visible',
                    state="visible", timeout=8000
                )
                log.append("Easy Apply modal confirmed open.")
            except Exception:
                log.append("Warning: modal not confirmed within 8s, proceeding anyway...")
            await _human_delay(800, 1500)
            result = await _fill_linkedin_easy_apply_form(page, app_data, log)
            return result

        if external_apply_btn:
            log.append("Clicking external Apply button and watching for navigation...")
            url_before = page.url
            try:
                async with page.expect_navigation(timeout=8000):
                    await external_apply_btn.click()
                external_url = page.url
            except Exception:
                external_url = page.url

            # If a modal appeared instead of a navigation, it's actually Easy Apply
            modal = await page.query_selector(
                '.jobs-easy-apply-modal, [data-test-modal-id="easy-apply-modal"], '
                '.artdeco-modal[role="dialog"], .top-level-modal-container'
            )
            if modal or external_url == url_before:
                log.append("Apply button opened a modal — treating as Easy Apply form.")
                result = await _fill_linkedin_easy_apply_form(page, app_data, log)
                return result

            if external_url and "linkedin.com" not in external_url.lower():
                redirected_ats = _detect_ats(external_url)
                log.append(f"Redirected to external portal: {redirected_ats.upper()} — {external_url}")
                redirect_data = dict(app_data)
                redirect_data["url"] = external_url
                if redirected_ats == "workday":
                    return await _apply_workday(page, redirect_data, creds, creds.get("linkedin_username", ""))
                elif redirected_ats == "greenhouse":
                    return await _apply_greenhouse(page, redirect_data, redirect_data.get("email", ""))
                elif redirected_ats == "lever":
                    return await _apply_lever(page, redirect_data, redirect_data.get("email", ""))
                else:
                    return await _fill_generic_form(page, redirect_data, log)

            return {
                "success": False,
                "intervention": True,
                "message": f"This job requires applying on the company website. Please complete manually at: {external_url or canonical_url}",
                "log": log,
            }

        return {
            "success": False,
            "intervention": True,
            "message": "Could not find the Apply button. The posting may have expired or LinkedIn layout changed.",
            "log": log,
        }

    except Exception as e:
        logger.exception("LinkedIn apply error")
        return {"success": False, "intervention": False, "message": f"Error: {str(e)}", "log": log}


async def _linkedin_login(page, creds: dict, log: list) -> bool:
    """
    Log into LinkedIn with stored credentials.
    Returns True on success, False if checkpoint/2FA/error/timeout detected.

    LinkedIn's login page is JS-rendered: DOMContentLoaded fires before the
    form fields are injected.  We wait explicitly for a known field to appear
    rather than relying on page-load events alone.
    """
    log.append("Navigating to LinkedIn login page...")
    try:
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
    except Exception as e:
        log.append(f"Could not navigate to LinkedIn login: {e}")
        return False

    # Wait for the email field to appear — the form is hydrated by JS after load.
    # We accept either the legacy #username id or the newer session_key name attr.
    EMAIL_SELECTOR = '#username, input[name="session_key"], input[autocomplete="username"]'
    PW_SELECTOR    = '#password, input[name="session_password"], input[type="password"]'
    try:
        await page.wait_for_selector(EMAIL_SELECTOR, state="visible", timeout=15000)
    except Exception:
        log.append("LinkedIn login form did not appear within 15 s. Page may be showing CAPTCHA or 2FA.")
        return False

    log.append("Login form ready — entering credentials...")

    # ── Strategy 1: label-based (most robust against DOM changes) ─────────────
    filled = False
    try:
        email_input = page.get_by_label("Email or phone").last
        pw_input    = page.get_by_label("Password").last
        await email_input.wait_for(state="visible", timeout=5000)
        await email_input.click()
        await _human_delay(100, 300)
        for ch in creds["linkedin_username"]:
            await page.keyboard.type(ch)
            await asyncio.sleep(random.uniform(0.04, 0.12))
        await _human_delay(200, 500)
        await pw_input.click()
        await _human_delay(100, 300)
        for ch in creds["linkedin_password"]:
            await page.keyboard.type(ch)
            await asyncio.sleep(random.uniform(0.04, 0.12))
        filled = True
    except Exception as e:
        log.append(f"Label-based fill failed ({type(e).__name__}), trying selector fallback...")

    # ── Strategy 2: CSS selector fallback ─────────────────────────────────────
    if not filled:
        try:
            await page.fill(EMAIL_SELECTOR, creds["linkedin_username"], timeout=8000)
            await page.fill(PW_SELECTOR,    creds["linkedin_password"], timeout=8000)
            filled = True
        except Exception as e:
            log.append(f"Selector-based fill also failed: {e}")
            return False

    # Submit
    await _human_delay(400, 800)
    try:
        # Prefer the exact "Sign in" button; fall back to any submit button
        submitted = False
        for btn_sel in [
            'button:has-text("Sign in")',
            'button[type="submit"]',
            'input[type="submit"]',
        ]:
            try:
                btn = await page.query_selector(btn_sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    submitted = True
                    break
            except Exception:
                continue
        if not submitted:
            log.append("Could not find submit button on login form.")
            return False
    except Exception as e:
        log.append(f"Submit click failed: {e}")
        return False

    # Wait for navigation after submit
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=20000)
    except Exception:
        pass
    await _human_delay(2000, 4000)

    current_url = page.url.lower()
    if "checkpoint" in current_url or "challenge" in current_url or "verify" in current_url:
        log.append("LinkedIn login requires additional verification (2FA/checkpoint). Please complete it manually.")
        return False
    if "login" in current_url:
        # Still on the login page — wrong credentials or error
        err_el = await page.query_selector('[data-test-id="alert-too-many-attempts"], .alert--error, .form__error')
        if err_el:
            err_text = (await err_el.inner_text()).strip()
            log.append(f"LinkedIn login failed: {err_text}")
        else:
            log.append("LinkedIn login failed — still on login page after submit.")
        return False

    log.append(f"LinkedIn login successful (landed on {page.url}).")
    return True


async def _ensure_linkedin_session(page, app_data: dict, log: list) -> bool:
    """
    Warm up the LinkedIn session before navigating to a job URL.

    Strategy:
      1. Navigate to /feed/ to test whether the injected cookies are still valid.
      2. If LinkedIn redirects to login/signup, fall back to credential login.
      3. Return True only when we can confirm the user is logged in.

    This prevents the /signup/cold-join redirect that occurs when cookies are stale
    and the agent goes straight to a job URL without an established session.
    """
    log.append("Warming up LinkedIn session...")
    try:
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=20000)
        await _human_delay(1500, 2500)
    except Exception as e:
        log.append(f"LinkedIn feed navigation failed: {e}")
        return False

    current_url = page.url.lower()
    logged_in_indicators = ("linkedin.com/feed", "linkedin.com/home", "linkedin.com/mynetwork", "linkedin.com/jobs")
    if any(ind in current_url for ind in logged_in_indicators):
        log.append("LinkedIn session active — proceeding to job URL.")
        return True

    # Redirected to login or signup — cookies are stale or absent.
    # Prefer AutoApply settings credentials; fall back to LinkedIn Connection credentials.
    log.append(f"Session not active (redirected to {page.url}). Attempting credential login...")

    username = (app_data.get("linkedin_username") or
                app_data.get("linkedin_session_email", ""))
    password = (app_data.get("linkedin_password") or
                app_data.get("linkedin_session_pw", ""))

    if not username or not password:
        log.append(
            "No LinkedIn credentials available for fallback login. "
            "Please reconnect LinkedIn in the dashboard (Settings → LinkedIn Connection)."
        )
        return False

    try:
        return await _linkedin_login(page, {"linkedin_username": username, "linkedin_password": password}, log)
    except Exception as e:
        log.append(f"LinkedIn credential login raised an unexpected error: {e}")
        return False


async def _fill_linkedin_easy_apply_form(page, app_data: dict, log: list) -> dict:
    """
    Navigate and fill the LinkedIn Easy Apply multi-step dialog.
    Handles: text inputs, phone, selects/dropdowns, number fields,
    file upload, and Next/Review/Submit/Done button progression.
    """
    # Resolve CV path to absolute so Playwright can find it
    cv_path = app_data.get("cv_path", "")
    if cv_path and not os.path.isabs(cv_path):
        cv_path = os.path.abspath(cv_path)

    # Wait for the Easy Apply modal to fully appear
    try:
        await page.wait_for_selector(
            '.jobs-easy-apply-modal, [data-test-modal-id="easy-apply-modal"], '
            '.artdeco-modal[role="dialog"], .top-level-modal-container',
            state="visible", timeout=8000
        )
        log.append("Easy Apply modal opened.")
    except Exception:
        log.append("Warning: Easy Apply modal not detected within 8s, attempting anyway...")

    max_steps = 15
    prev_step_html = ""

    for step in range(max_steps):
        await _human_delay(800, 1500)
        log.append(f"Easy Apply step {step + 1}...")

        # ── Check for CAPTCHA ──────────────────────────────────────────────
        if await page.query_selector('iframe[title*="captcha"]') or \
           await page.query_selector('[class*="captcha"]'):
            return {
                "success": False, "intervention": True,
                "message": "CAPTCHA detected on LinkedIn Easy Apply. Please solve it manually.",
                "log": log,
            }

        # ── Check for early success (confirmation text visible) ────────────
        # Generic "Done" or "Dismiss" buttons are too risky if they belong to cookies/popups.
        # We require specific confirmation text for a success return.
        success_indicators = [
            'h2:has-text("Application submitted")',
            'h3:has-text("Your application was sent")',
            'h2:has-text("applied")',
            '.artdeco-toast-item--success'
        ]
        for indicator in success_indicators:
            el = await page.query_selector(indicator)
            if el and await el.is_visible():
                log.append(f"Application success confirmed via indicator: {indicator}")
                return {"success": True, "intervention": False,
                        "message": "Applied via LinkedIn Easy Apply.", "log": log}

        # ── Phone number ───────────────────────────────────────────────────
        phone_field = await page.query_selector('input[id*="phoneNumber"], input[name*="phone"]')
        if phone_field and await phone_field.is_visible():
            val = await phone_field.input_value()
            if not val and app_data.get("phone"):
                await phone_field.fill(app_data["phone"])
                await _human_delay(200, 500)

        # ── All visible text/email/number inputs ───────────────────────────
        text_inputs = await page.query_selector_all(
            'input[type="text"], input[type="email"], input[type="number"], input[type="tel"]'
        )
        for inp in text_inputs:
            try:
                if not await inp.is_visible():
                    continue
                val = await inp.input_value()
                if val:
                    continue  # already filled

                # Try to read associated label text
                input_id = await inp.get_attribute("id") or ""
                label_text = ""
                if input_id:
                    lbl = await page.query_selector(f'label[for="{input_id}"]')
                    if lbl:
                        label_text = (await lbl.text_content() or "").lower()

                # Fallback: look for closest label via aria-labelledby
                if not label_text:
                    labelledby = await inp.get_attribute("aria-labelledby") or ""
                    if labelledby:
                        lbl_el = await page.query_selector(f'#{labelledby}')
                        if lbl_el:
                            label_text = (await lbl_el.text_content() or "").lower()

                placeholder = (await inp.get_attribute("placeholder") or "").lower()
                combined = label_text + " " + placeholder

                if "city" in combined or "location" in combined:
                    await inp.fill(app_data.get("location", "Zurich"))
                elif "linkedin" in combined:
                    await inp.fill(app_data.get("linkedin_url", ""))
                elif "phone" in combined or "mobile" in combined:
                    if app_data.get("phone"):
                        await inp.fill(app_data["phone"])
                elif "year" in combined and ("experience" in combined or "exp" in combined):
                    # "How many years of experience..." — fill with sensible default
                    await inp.fill("8")
                elif "salary" in combined or "compensation" in combined:
                    await inp.fill("140000")
                elif await inp.get_attribute("type") == "number":
                    # Generic number field — fill with 1 as safe default
                    await inp.fill("1")
                await _human_delay(100, 300)
            except Exception:
                continue

        # ── Select / dropdown elements ─────────────────────────────────────
        selects = await page.query_selector_all('select')
        for sel_el in selects:
            try:
                if not await sel_el.is_visible():
                    continue
                current_val = await sel_el.input_value()
                if current_val and current_val not in ("", "Select an option", "-- Select --"):
                    continue  # already has a value

                # Get all options
                options = await sel_el.query_selector_all('option')
                non_empty_opts = []
                for opt in options:
                    v = await opt.get_attribute("value") or ""
                    t = (await opt.text_content() or "").strip()
                    if v and t and t.lower() not in ("select an option", "-- select --",
                                                      "choose an option", "please select"):
                        non_empty_opts.append(v)

                if non_empty_opts:
                    # Pick "Yes" if available (for work-auth type questions), else first option
                    yes_opt = next((v for v in non_empty_opts if v.lower() in ("yes", "true")), None)
                    await sel_el.select_option(yes_opt or non_empty_opts[0])
                    log.append(f"Selected dropdown option: {yes_opt or non_empty_opts[0]}")
                    await _human_delay(200, 400)
            except Exception:
                continue

        # ── File upload (CV/Resume) ────────────────────────────────────────
        upload_field = await page.query_selector('input[type="file"]')
        if upload_field and cv_path and os.path.exists(cv_path):
            try:
                log.append("Uploading CV...")
                await upload_field.set_input_files(cv_path)
                await _human_delay(1500, 2500)
            except Exception as ue:
                log.append(f"CV upload warning: {ue}")

        # ── Detect Submit / Review / Next / Done buttons ───────────────────
        submit_btn = None
        next_btn = None

        # "Submit application" is the final step
        for sel in [
            'button:has-text("Submit application")', 
            'button:has-text("Submit")',
            'button[aria-label*="Submit application"]'
        ]:
            b = await page.query_selector(sel)
            if b and await b.is_visible():
                submit_btn = b
                break
        
        # "Review" precedes Submit
        if not submit_btn:
            for sel in ['button:has-text("Review")', 'button[aria-label*="Review your application"]']:
                b = await page.query_selector(sel)
                if b and await b.is_visible():
                    submit_btn = b  # treat Review as a submit-path button
                    break

        # "Next" / "Continue"
        if not submit_btn:
            for sel in [
                'button:has-text("Next")', 
                'button:has-text("Continue")', 
                'button:has-text("Weiter")',
                'button[aria-label*="Continue to next step"]'
            ]:
                b = await page.query_selector(sel)
                if b and await b.is_visible():
                    next_btn = b
                    break

        # Vision Fallback for navigation buttons
        if not submit_btn and not next_btn:
            log.append("Navigation buttons not found in form. Attempting Vision recovery...")
            vision_id = await _identify_with_vision(page, "Find the 'Next', 'Review', 'Continue', or 'Submit application' button to proceed.", log)
            if vision_id:
                target = await page.query_selector(f'[data-cr-id="{vision_id}"]')
                if target:
                    text = (await target.inner_text() or "").lower()
                    # Filter out obvious navigation icons or unrelated elements
                    if any(nav in text for nav in ["home", "jobs", "messaging", "notifications", "me"]):
                        log.append(f"Vision recovery misidentified navigation element {vision_id} as button. Skipping.")
                    elif "submit" in text or "review" in text:
                        submit_btn = target
                        log.append(f"Vision recovery matched: SUBMIT (via ID {vision_id})")
                        # Add force-click for vision targets too
                        try:
                            await target.click(force=True, timeout=5000)
                        except Exception:
                            await page.evaluate("el => el.click()", target)
                    else:
                        next_btn = target
                        log.append(f"Vision recovery matched: NEXT (via ID {vision_id})")
                        # Add force-click for vision targets too
                        try:
                            await target.click(force=True, timeout=5000)
                        except Exception:
                            await page.evaluate("el => el.click()", target)

        # ── Detect stuck state (same page for 2 iterations) ───────────────
        try:
            current_html = await page.inner_html('.jobs-easy-apply-modal, .artdeco-modal, .top-level-modal-container') or ""
        except Exception:
            current_html = ""

        if submit_btn:
            # Uncheck "Follow company" if present
            for follow_sel in ['input[id*="follow-company"]', 'input[aria-label*="follow"]']:
                fc = await page.query_selector(follow_sel)
                if fc:
                    try: await fc.uncheck()
                    except Exception: pass

            log.append("Clicking Submit application...")
            try:
                # Force click to bypass transparent overlays
                await submit_btn.click(force=True, timeout=5000)
            except Exception:
                await page.evaluate("el => el.click()", submit_btn)
            await _human_delay(3000, 5000)

            # Check for success confirmation
            for conf_sel in [
                '[data-test-modal-id="post-apply-modal"]',
                'h2:has-text("Application submitted")',
                'h3:has-text("Your application was sent")',
                '.artdeco-toast-item--success',
                'h2:has-text("applied")',
                'button:has-text("Done")',
                'button:has-text("Dismiss")',
            ]:
                conf = await page.query_selector(conf_sel)
                if conf and await conf.is_visible():
                    log.append("Application submitted successfully!")
                    try: await conf.click()
                    except Exception: pass
                    return {"success": True, "intervention": False,
                            "message": "Applied via LinkedIn Easy Apply.", "log": log}

            # If no confirmation found, treat as another step and keep going
            log.append("Submit clicked — checking for next step or confirmation...")

        elif next_btn:
            # Check if Next is disabled (required fields not filled)
            is_disabled = await next_btn.get_attribute("disabled")
            aria_disabled = await next_btn.get_attribute("aria-disabled")
            if is_disabled is not None or aria_disabled == "true":
                log.append("Next button is disabled — required fields may be empty. Stopping.")
                break

            log.append("Clicking Next...")
            try:
                # Force click to bypass transparent overlays
                await next_btn.click(force=True, timeout=5000)
            except Exception:
                await page.evaluate("el => el.click()", next_btn)
            
            # Wait for form to transition to next step
            await _human_delay(1200, 2000)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception:
                pass

        else:
            # No navigation button found
            if current_html and current_html == prev_step_html:
                log.append("Form appears stuck — no progress detected.")
                break
            log.append("No Next/Submit button found — checking for completion...")
            # One last success check - must be specific
            for conf_sel in ['h2:has-text("Application submitted")', 'h3:has-text("Your application was sent")']:
                conf = await page.query_selector(conf_sel)
                if conf and await conf.is_visible():
                    return {"success": True, "intervention": False,
                            "message": "Applied via LinkedIn Easy Apply.", "log": log}
            break

        prev_step_html = current_html

    # Final check after loop - must be specific
    for conf_sel in [
        'h2:has-text("Application submitted")',
        'h3:has-text("Your application was sent")',
    ]:
        conf = await page.query_selector(conf_sel)
        if conf and await conf.is_visible():
            return {"success": True, "intervention": False,
                    "message": "Applied via LinkedIn Easy Apply.", "log": log}

    return {
        "success": False,
        "intervention": True,
        "message": (
            "LinkedIn Easy Apply needs manual completion — likely has required questions "
            "(e.g. work authorization, specific screening questions) that need your input. "
            "The browser window is still open. Please complete the form manually and click Submit, "
            "then click 'Resume Automation' in the app."
        ),
        "log": log,
    }


async def _apply_workday(page, app_data: dict, creds: dict, user_email: str) -> dict:
    """Workday ATS application flow."""
    log = []
    try:
        log.append("Navigating to Workday job posting...")
        await page.goto(app_data["url"], wait_until="domcontentloaded", timeout=30000)
        await _human_delay(2000, 4000)

        # Check for "Sign in with LinkedIn"
        li_signin = await page.query_selector('button:has-text("LinkedIn")') or \
                    await page.query_selector('[aria-label*="LinkedIn"]') or \
                    await page.query_selector('a:has-text("Sign in with LinkedIn")')
        if li_signin and creds.get("linkedin_username"):
            log.append("Attempting 'Sign in with LinkedIn'...")
            # The click MUST happen inside expect_popup so Playwright can intercept the new window
            try:
                async with page.expect_popup(timeout=10000) as popup_info:
                    await li_signin.click()
                popup = await popup_info.value
                if popup:
                    login_ok = await _linkedin_login(popup, creds, log)
                    if not login_ok:
                        log.append("LinkedIn SSO login needs manual verification — continuing without SSO.")
                    else:
                        await popup.wait_for_close(timeout=20000)
            except Exception as popup_err:
                # No popup opened — LinkedIn SSO may have redirected in the same tab
                log.append(f"LinkedIn SSO popup not detected ({popup_err}), checking page state...")
            await _human_delay(2000, 3000)

        # Click "Apply"
        apply_btn = await page.query_selector('a[data-automation-id*="Apply"]') or \
                    await page.query_selector('button:has-text("Apply")')
        if not apply_btn:
            return {
                "success": False,
                "intervention": True,
                "message": "Could not find the Apply button on this Workday posting.",
                "log": log
            }
        await apply_btn.click()
        await _human_delay(2000, 4000)

        # Account creation / login
        create_account_btn = await page.query_selector('a:has-text("Create Account")') or \
                             await page.query_selector('button:has-text("Create Account")')
        existing_login_btn = await page.query_selector('input#username')

        new_account = None
        if existing_login_btn:
            # Try existing email login
            await _type_like_human(page, 'input#username', user_email)
            pwd_field = await page.query_selector('input#password')
            if pwd_field:
                # We don't know the existing Workday password — needs intervention
                return {
                    "success": False,
                    "intervention": True,
                    "message": f"Workday requires login for this company. Please enter your password for {user_email} on the job portal, then click 'Resume Automation'.",
                    "log": log,
                }
        elif create_account_btn:
            # Create a new account
            await create_account_btn.click()
            await _human_delay(1500, 3000)
            password = _generate_password()
            new_account = {
                "platform_name": f"Workday @ {app_data.get('company', 'unknown')}",
                "platform_url": app_data["url"],
                "username": user_email,
                "password": password,
                "notes": "Account auto-created during job application",
            }

            # Fill registration form
            email_fields = await page.query_selector_all('input[type="email"]')
            for f in email_fields:
                await f.fill(user_email)
            pass_fields = await page.query_selector_all('input[type="password"]')
            for f in pass_fields:
                await f.fill(password)
            await _human_delay(500, 1000)

            confirm_btn = await page.query_selector('button:has-text("Create Account")') or \
                          await page.query_selector('button[type="submit"]')
            if confirm_btn:
                await confirm_btn.click()
                await _human_delay(3000, 5000)

            # Check for email verification notice
            if await page.query_selector('text=verify') or await page.query_selector('text=check your email'):
                return {
                    "success": False,
                    "intervention": True,
                    "message": "Email verification required. Please check your inbox and click the verification link, then click 'Resume Automation'.",
                    "log": log,
                    "new_account": new_account,
                }

        # Generic form fill
        result = await _fill_generic_form(page, app_data, log)
        result["new_account"] = new_account
        return result

    except Exception as e:
        logger.exception("Workday apply error")
        return {"success": False, "intervention": False, "message": f"Error: {str(e)}", "log": log}


async def _apply_greenhouse(page, app_data: dict, user_email: str) -> dict:
    """Greenhouse ATS application flow."""
    log = []
    try:
        log.append("Navigating to Greenhouse job posting...")
        await page.goto(app_data["url"], wait_until="domcontentloaded", timeout=30000)
        await _human_delay(1500, 3000)

        # Greenhouse typically has a direct form
        log.append("Filling Greenhouse application form...")

        # Upload CV
        upload = await page.query_selector('input[type="file"]')
        if upload and app_data.get("cv_path") and os.path.exists(app_data["cv_path"]):
            log.append("Uploading CV...")
            await upload.set_input_files(app_data["cv_path"])
            await _human_delay(1500, 3000)

        # Fill standard fields
        for selector, value in [
            ('#first_name', app_data.get("first_name", "")),
            ('#last_name', app_data.get("last_name", "")),
            ('#email', user_email),
            ('#phone', app_data.get("phone", "")),
        ]:
            field = await page.query_selector(selector)
            if field and value:
                await field.fill("")
                await _type_like_human(page, selector, value)
                await _human_delay(200, 500)

        # Cover letter (textarea)
        cl_field = await page.query_selector('textarea[name*="cover"]') or \
                   await page.query_selector('#cover_letter_text')
        if cl_field and app_data.get("cover_letter"):
            await cl_field.fill(app_data["cover_letter"][:3000])
            await _human_delay(500, 1000)

        # Submit
        submit = await page.query_selector('#submit_app')
        if submit:
            log.append("Submitting application...")
            await submit.click()
            await _human_delay(3000, 5000)
            if "confirmation" in page.url or await page.query_selector('text=thank you'):
                log.append("Greenhouse application submitted!")
                return {"success": True, "intervention": False, "message": "Applied via Greenhouse.", "log": log}

        return {
            "success": False,
            "intervention": True,
            "message": "Greenhouse submission could not be confirmed. Please check and complete manually.",
            "log": log,
        }
    except Exception as e:
        logger.exception("Greenhouse apply error")
        return {"success": False, "intervention": False, "message": f"Error: {str(e)}", "log": log}


async def _apply_lever(page, app_data: dict, user_email: str) -> dict:
    """Lever ATS application flow (jobs.lever.co)."""
    log = []
    try:
        log.append("Navigating to Lever job posting...")
        await page.goto(app_data["url"], wait_until="domcontentloaded", timeout=30000)
        await _human_delay(1500, 3000)

        # Click Apply button if present
        apply_btn = await page.query_selector('a.postings-btn:has-text("Apply")') or \
                    await page.query_selector('a:has-text("Apply for this job")')
        if apply_btn:
            log.append("Clicking Apply button...")
            await apply_btn.click()
            await _human_delay(1500, 3000)

        log.append("Filling Lever application form...")

        # Upload CV
        upload = await page.query_selector('input[type="file"]')
        if upload and app_data.get("cv_path") and os.path.exists(app_data["cv_path"]):
            log.append("Uploading CV...")
            await upload.set_input_files(app_data["cv_path"])
            await _human_delay(1500, 3000)

        # Standard Lever field IDs
        for selector, value in [
            ('input[name="name"]', f"{app_data.get('first_name', '')} {app_data.get('last_name', '')}".strip()),
            ('input[name="email"]', user_email),
            ('input[name="phone"]', app_data.get("phone", "")),
            ('input[name="org"]', app_data.get("company", "")),
            ('input[name="urls[LinkedIn]"]', app_data.get("linkedin_url", "")),
        ]:
            field = await page.query_selector(selector)
            if field and value:
                await field.fill("")
                await field.fill(value)
                await _human_delay(200, 400)

        # Cover letter textarea
        cl_field = await page.query_selector('textarea[name="comments"]') or \
                   await page.query_selector('textarea[name*="cover"]')
        if cl_field and app_data.get("cover_letter"):
            await cl_field.fill(app_data["cover_letter"][:3000])
            await _human_delay(500, 1000)

        # Submit
        submit = await page.query_selector('button[type="submit"]:has-text("Submit application")') or \
                 await page.query_selector('button[type="submit"]')
        if submit:
            log.append("Submitting application...")
            await submit.click()
            await _human_delay(3000, 5000)
            if "thanks" in page.url or "confirmation" in page.url or \
               await page.query_selector('h2:has-text("Thank")') or \
               await page.query_selector('text=application has been submitted'):
                log.append("Lever application submitted!")
                return {"success": True, "intervention": False, "message": "Applied via Lever.", "log": log}

        return {
            "success": False,
            "intervention": True,
            "message": "Lever submission could not be confirmed. Please check and complete manually.",
            "log": log,
        }
    except Exception as e:
        logger.exception("Lever apply error")
        return {"success": False, "intervention": False, "message": f"Error: {str(e)}", "log": log}


async def _apply_jobsch(page, app_data: dict, user_email: str) -> dict:
    """Jobs.ch application flow — typically redirects to company ATS or has a native apply form."""
    log = []
    try:
        log.append("Navigating to jobs.ch posting...")
        await page.goto(app_data["url"], wait_until="domcontentloaded", timeout=30000)
        await _human_delay(2000, 4000)

        # jobs.ch often has a direct "Jetzt bewerben" / "Apply now" button that redirects to company portal
        apply_btn = await page.query_selector('a:has-text("Jetzt bewerben")') or \
                    await page.query_selector('a:has-text("Apply now")') or \
                    await page.query_selector('button:has-text("Jetzt bewerben")') or \
                    await page.query_selector('a[data-cy="apply-button"]') or \
                    await page.query_selector('a.job-application-link')

        if apply_btn:
            # Capture where this redirects — may go to an external company ATS
            external_url = await apply_btn.get_attribute("href") or ""
            if external_url and "jobs.ch" not in external_url.lower():
                # Redirects to company ATS — detect and route
                redirected_ats = _detect_ats(external_url)
                log.append(f"jobs.ch redirects to: {redirected_ats.upper()} — {external_url}")
                redirect_data = dict(app_data)
                redirect_data["url"] = external_url
                if redirected_ats == "workday":
                    return await _apply_workday(page, redirect_data, app_data, user_email)
                elif redirected_ats == "greenhouse":
                    return await _apply_greenhouse(page, redirect_data, user_email)
                elif redirected_ats == "lever":
                    return await _apply_lever(page, redirect_data, user_email)
                else:
                    log.append("Clicking apply button to navigate to form...")
                    async with page.expect_navigation(timeout=15000):
                        await apply_btn.click()
                    await _human_delay(2000, 4000)
                    # Re-detect after navigation
                    new_ats = _detect_ats(page.url)
                    if new_ats != "generic":
                        redirect_data["url"] = page.url
                        if new_ats == "workday":
                            return await _apply_workday(page, redirect_data, app_data, user_email)
                        elif new_ats == "greenhouse":
                            return await _apply_greenhouse(page, redirect_data, user_email)
                        elif new_ats == "lever":
                            return await _apply_lever(page, redirect_data, user_email)
                    return await _fill_generic_form(page, redirect_data, log)
            else:
                log.append("Clicking apply button...")
                await apply_btn.click()
                await _human_delay(2000, 4000)
                return await _fill_generic_form(page, app_data, log)

        return {
            "success": False,
            "intervention": True,
            "message": "Could not find the Apply button on jobs.ch. Please apply manually.",
            "log": log,
        }
    except Exception as e:
        logger.exception("jobs.ch apply error")
        return {"success": False, "intervention": False, "message": f"Error: {str(e)}", "log": log}


async def _fill_generic_form(page, app_data: dict, log: list) -> dict:
    """
    Generic form filler: tries to fill common fields and upload CV.
    Falls back to intervention if it can't determine progress.
    """
    log.append("Running generic form-fill strategy...")

    # Upload CV if file upload present
    upload = await page.query_selector('input[type="file"]')
    if upload and app_data.get("cv_path") and os.path.exists(app_data["cv_path"]):
        log.append("Uploading CV...")
        await upload.set_input_files(app_data["cv_path"])
        await _human_delay(1500, 3000)

    # Fill email
    for sel in ['input[type="email"]', 'input[name*="email"]', 'input[id*="email"]']:
        field = await page.query_selector(sel)
        if field:
            val = await field.input_value()
            if not val:
                await field.fill(app_data.get("email", ""))
                break

    # Fill name fields
    for sel in ['input[name*="first"]', 'input[id*="first"]', 'input[placeholder*="First"]']:
        field = await page.query_selector(sel)
        if field:
            val = await field.input_value()
            if not val:
                await field.fill(app_data.get("first_name", ""))

    for sel in ['input[name*="last"]', 'input[id*="last"]', 'input[placeholder*="Last"]']:
        field = await page.query_selector(sel)
        if field:
            val = await field.input_value()
            if not val:
                await field.fill(app_data.get("last_name", ""))

    # Check for CAPTCHA
    if await page.query_selector('iframe[title*="reCAPTCHA"]') or \
       await page.query_selector('[class*="captcha"]'):
        return {
            "success": False,
            "intervention": True,
            "message": "CAPTCHA detected. Please solve it in the open browser window, then click 'Resume Automation'.",
            "log": log,
        }

    # Try finding submit button
    submit = await page.query_selector('button[type="submit"]') or \
             await page.query_selector('input[type="submit"]') or \
             await page.query_selector('button:has-text("Submit")') or \
             await page.query_selector('button:has-text("Apply")')

    if not submit:
        return {
            "success": False,
            "intervention": True,
            "message": "This application form requires manual completion. Please fill in remaining fields and submit, then click 'Resume Automation'.",
            "log": log,
        }

    log.append("Submitting application...")
    await submit.click()
    await _human_delay(3000, 5000)
    log.append("Form submitted.")
    return {"success": True, "intervention": False, "message": "Application submitted via generic form.", "log": log}


# ─────────────────────────────────────────────────────────────────────────────
# Universal Interaction Loop (The Cognitive Engine)
# ─────────────────────────────────────────────────────────────────────────────

async def _universal_interaction_loop(page, app_data: dict, user_email: str, ats_hint: str = "generic") -> dict:
    """
    Unified loop that uses Gemini Vision to navigate any site and complete applications.
    """
    log = [f"Starting Universal Interaction Loop (Hint: {ats_hint})"]
    step_history = []
    max_steps = 25
    llm = LLMAnalysisService()
    
    # 1. Initial Navigation
    try:
        log.append(f"Navigating to {app_data['url']}")
        await page.goto(app_data["url"], wait_until="domcontentloaded", timeout=45000)
        await _human_delay(2000, 4000)
    except Exception as e:
        log.append(f"Initial navigation failed: {str(e)}")
        return {"success": False, "intervention": False, "message": f"Navigation error: {str(e)}", "log": log}

    # 2. Main Loop
    for step in range(max_steps):
        log.append(f"--- Cognitive Step {step + 1} ---")
        
        # A. Recursive Cleanup: Ensure no overlays are blocking the view
        # We do this up to 3 times to handle layered popups (e.g. Cookie -> Sign In)
        for i in range(3):
            if await _dismiss_overlays(page, log):
                await _human_delay(1000, 2000)
            else:
                break
        
        # B. Check for Login Wall on Job Page
        # If we see a sign-in modal/wall but we are supposed to be logged in, 
        # we try to close it once, or re-verify session.
        if await page.query_selector('.modal__overlay--visible, [data-test-id="auth-wall"], .login-modal'):
            log.append("Detected potential Login Wall / Modal. Attempting to dismiss or handle...")
            # Try specific dismiss button for LinkedIn's 'Sign in to see more'
            dismiss = await page.query_selector('.modal__dismiss, button[aria-label="Dismiss"], button[aria-label="Close"]')
            if dismiss:
                log.append("Found dismiss button for Auth Modal. Clicking...")
                await dismiss.click()
                await _human_delay(1500, 2500)
        
        # C. Label elements
        try:
            labeled_count = await page.evaluate(_LABEL_ELEMENTS_JS)
            log.append(f"Labeled {labeled_count} elements.")
        except Exception as e:
            log.append(f"Error labeling elements: {str(e)}")
        
        # C. Take screenshot
        screenshot = await page.screenshot(type="png", full_page=False)
        
        # D. Decide action
        decision = await llm.decide_universal_apply_action(
            screenshot_bytes=screenshot,
            page_url=page.url,
            user_profile=app_data, # Contains all user details
            step_history=step_history
        )
        
        # Clean up labels
        await page.evaluate("document.querySelectorAll('.cr-vision-label').forEach(e => e.remove())")
        
        log.append(f"Decision: {decision.get('action')} - {decision.get('reasoning')}")
        step_history.append(f"{decision.get('action')}: {decision.get('reasoning')}")
        
        # E. Process Decision
        action = decision.get("action")
        current_stage = decision.get("current_stage")
        account_meta = decision.get("account_metadata", {})
        
        if account_meta.get("is_creating_account"):
            log.append(f"Detected account creation for platform: {account_meta.get('platform_name')}")
            # The AutoApplyAgent.run_automation method will handle saving this to DB
            # if we include it in the return dict.
            result_account = {
                "platform_name": account_meta.get("platform_name"),
                "platform_url": page.url,
                "username": account_meta.get("username") or app_data.get("email"),
                "password": account_meta.get("password") or "Auto-generated",
                "notes": f"Created during {current_stage} stage"
            }
        else:
            result_account = None

        if action == "FINISH_SUCCESS" or decision.get("is_success_page"):
            log.append("LLM confirmed application success page. Running final validation...")
            
            # Final Validation Lock: Check for email confirmation
            email_verified = False
            if app_data.get("email_username") and app_data.get("email_password"):
                log.append("Polling email for confirmation...")
                verifier = EmailVerificationService(app_data["email_username"], app_data["email_password"])
                # Wait a bit for email to arrive
                await asyncio.sleep(10)
                email_verified = await verifier.verify_confirmation(app_data.get("company", ""), app_data.get("job_title", ""))
                if email_verified:
                    log.append("Email confirmation received! Double-lock success verified.")
                else:
                    log.append("No confirmation email found yet (this is common, visual success still holds).")

            return {
                "success": True, 
                "intervention": False, 
                "message": "Applied successfully. Visual confirmation verified." + (" Email verified." if email_verified else ""), 
                "log": log,
                "new_account": result_account
            }
            
        if action == "INTERVENTION":
            log.append(f"Intervention required: {decision.get('reason')}")
            return {"success": False, "intervention": True, "message": decision.get("reason", "Agent got stuck."), "log": log}
            
        if action == "WAIT":
            await _human_delay(3000, 5000)
            continue
            
        # F. Execute Action
        try:
            executed = await _execute_agent_action(page, decision, app_data, log)
            if not executed:
                log.append("Action execution failed or was skipped.")
        except Exception as e:
            log.append(f"Error executing action {action}: {str(e)}")
            
        await _human_delay(1500, 3000)
        
        # Check for URL change as progress indicator
        if step > 0 and step % 5 == 0:
            log.append(f"Step {step}: Current URL is {page.url}")

    return {
        "success": False,
        "intervention": True,
        "message": "Maximum steps reached without confirmation.",
        "log": log
    }

async def _dismiss_overlays(page, log) -> bool:
    """Attempt to clear common blocking elements. Returns True if something was clicked."""
    dismissed = False
    for sel in [
        'button:has-text("Accept")', 'button:has-text("Agree")', 'button:has-text("Akzeptieren")',
        'button[aria-label="Dismiss"]', 'button[aria-label="Close"]', 'button[aria-label="Close modal"]',
        '.artdeco-modal__dismiss', '.modal__close', '.privacy-policy-banner__dismiss',
        'button:has-text("Reject")', 'button:has-text("Ablehnen")',
        '.artdeco-toast-item__dismiss', 'button:has-text("Agree & Join")',
        'button:has-text("Maybe later")', 'button:has-text("Not now")',
        'button[aria-label="Dismiss notification"]',
        '.p0.m0.artdeco-button--tertiary[aria-label*="Dismiss"]' # LinkedIn specific
    ]:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                await el.click(timeout=2000)
                log.append(f"Dismissed overlay: {sel}")
                dismissed = True
                # Small delay between multiple dismissals
                await asyncio.sleep(0.5)
        except Exception:
            pass
    return dismissed

async def _execute_agent_action(page, decision: dict, app_data: dict, log: list) -> bool:
    """Helper to perform the Playwright action decided by the LLM."""
    action = decision.get("action")
    element_id = decision.get("element_id")
    value = decision.get("value")
    
    if not element_id and action not in ["WAIT", "FINISH_SUCCESS", "INTERVENTION"]:
        log.append(f"Warning: {action} requested but no element_id provided.")
        return False
        
    selector = f'[data-cr-id="{element_id}"]'
    target = await page.query_selector(selector)
    if not target:
        log.append(f"Error: Element [{element_id}] not found on page.")
        return False

    if action == "CLICK":
        log.append(f"Action: Clicking element [{element_id}]")
        try:
            await target.click(timeout=5000)
        except Exception:
            await page.evaluate("el => el.click()", target) # Force click via JS
        return True
        
    if action == "TYPE":
        log.append(f"Action: Typing into element [{element_id}]")
        await target.scroll_into_view_if_needed()
        await target.fill("") # Clear first
        await target.type(value or "", delay=random.randint(50, 150))
        return True
        
    if action == "UPLOAD":
        log.append(f"Action: Uploading file to element [{element_id}]")
        cv_path = app_data.get("cv_path")
        if cv_path and os.path.exists(cv_path):
            await target.set_input_files(cv_path)
            return True
        log.append("Upload failed: CV path missing or file not found.")
        return False
        
    if action == "SELECT":
        log.append(f"Action: Selecting '{value}' in element [{element_id}]")
        await target.select_option(label=value) if value else None
        return True
        
    return False

def _run_playwright_in_thread(ats: str, app_data: dict, user_email: str, linkedin_cookies: list = None) -> dict:
    """
    Run the full Playwright browser session in a dedicated thread with its own
    event loop. Required on Windows because FastAPI's SelectorEventLoop cannot
    spawn subprocesses (Playwright needs ProactorEventLoop on Windows).

    Uses the new ApplyOrchestrator (state machine + LLMBridge) instead of the
    legacy monolithic interaction loop.
    """
    async def _browser_session():
        from playwright.async_api import async_playwright
        from agents.apply_engine.orchestrator import ApplyOrchestrator
        import json as _json_mod
        import pathlib
        import os

        profile_dir = os.path.join(
            os.getcwd(), "browser_profiles",
            user_email.replace("@", "_").replace(".", "_")
        )
        os.makedirs(profile_dir, exist_ok=True)

        # Reset Chromium's crash flag before launch so the "Chromium didn't shut
        # down correctly" restore dialog never appears.  The flag is written when
        # Chromium exits uncleanly (e.g. the previous context wasn't closed).
        _prefs = pathlib.Path(profile_dir) / "Default" / "Preferences"
        if _prefs.exists():
            try:
                _pdata = _json_mod.loads(_prefs.read_text(encoding="utf-8"))
                _pdata.setdefault("profile", {})["exit_type"] = "Normal"
                _pdata.setdefault("profile", {})["exited_cleanly"] = True
                _prefs.write_text(_json_mod.dumps(_pdata), encoding="utf-8")
            except Exception as _e:
                logger.warning(f"Could not reset Chromium exit flag: {_e}")

        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                viewport=_random_viewport(),
                extra_http_headers=_stealth_headers(),
                user_agent=_stealth_headers()["User-Agent"],
            )

            try:
                # Inject LinkedIn session cookies to bypass login
                if ats == "linkedin" and linkedin_cookies:
                    try:
                        await context.add_cookies(linkedin_cookies)
                        logger.info(f"Injected {len(linkedin_cookies)} LinkedIn cookies.")
                    except Exception as e:
                        logger.warning(f"Cookie injection failed: {e}")

                # Stealth: hide webdriver flag
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
                """)

                page = context.pages[0] if context.pages else await context.new_page()

                # For LinkedIn: verify the session is live before navigating to the job URL.
                # Stale cookies cause /signup/cold-join redirects if we skip this step.
                session_log: list = []
                if ats == "linkedin":
                    session_ok = await _ensure_linkedin_session(page, app_data, session_log)
                    for line in session_log:
                        logger.info(line)
                    if not session_ok:
                        return {
                            "success": False,
                            "intervention": True,
                            "message": (
                                "Could not establish a LinkedIn session. "
                                "Please reconnect LinkedIn from the dashboard "
                                "(Settings → LinkedIn Connection) and try again."
                            ),
                            "log": session_log,
                        }

                # Run the new state-machine orchestrator with user's preferred AI provider
                orchestrator = ApplyOrchestrator(provider=app_data.get("llm_provider", "gemini"))
                apply_result = await orchestrator.run(page, app_data)

                logger.info(f"Orchestrator call summary: {orchestrator.call_summary()}")

                await _human_delay(2000, 4000)
                result_dict = apply_result.to_dict()
                # Prepend session warm-up log so the user can see the login steps
                # in the intervention/result modal, not just in the server log.
                if session_log:
                    result_dict["log"] = session_log + result_dict.get("log", [])
                return result_dict

            finally:
                # Always close cleanly so Chromium marks exit_type=Normal.
                # Without this, any unhandled exception leaves the profile in
                # "Crashed" state and triggers the restore dialog on next launch.
                try:
                    await context.close()
                except Exception:
                    pass

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
    else:
        loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_browser_session())
    finally:
        loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# Main AutoApplyAgent class
# ─────────────────────────────────────────────────────────────────────────────

class AutoApplyAgent:
    """Orchestrates the full auto-apply process for a given JobApplication."""

    def __init__(self, db: Session):
        self.db = db

    def _set_status(self, app: JobApplication, status: str, message: str = "", log_lines: list = None):
        """Update application status and feedback fields in DB."""
        app.status = status
        if message:
            app.intervention_message = message
        if log_lines:
            existing = json.loads(app.auto_apply_log or "[]")
            existing.extend(log_lines)
            app.auto_apply_log = json.dumps(existing)
        self.db.commit()

    def _get_app_data(self, application: JobApplication, user: User, profile: UserProfile, creds: Optional[AutoApplyCredential]) -> dict:
        """Build the app_data dict passed to platform strategies."""
        full_name = (user.full_name or "").strip()
        name_parts = full_name.split(" ", 1)

        # Get URL — prefer job.application_url, else application.application_url
        url = application.application_url or ""
        company = ""
        job_title = ""
        if application.job_opportunity_id:
            job = self.db.query(JobOpportunity).filter(JobOpportunity.id == application.job_opportunity_id).first()
            if job:
                url = url or job.application_url
                company = job.company
                job_title = job.title

        return {
            "url": url,
            "company": company,
            "job_title": job_title,
            "email": user.email,
            "first_name": name_parts[0] if name_parts else "",
            "last_name": name_parts[1] if len(name_parts) > 1 else "",
            "phone": profile.phone if profile else "",
            "location": profile.location if profile else "",
            "linkedin_url": profile.linkedin_url if profile else "",
            "cv_path": application.cv_path,
            "cover_letter": application.cover_letter,
            "linkedin_username": creds.linkedin_username if creds else "",
            "linkedin_password": decrypt_value(creds.linkedin_password_enc) if creds else "",
            "email_username": creds.email_username if creds else "",
            "email_password": decrypt_value(creds.email_password_enc) if creds else "",
            "llm_provider": (creds.llm_provider or "gemini") if creds else "gemini",
        }

    async def run_automation(self, application_id: int) -> dict:
        """
        Main entry point. Launches Playwright, detects ATS, runs the correct strategy.
        Handles feedback loop and account tracking.
        """
        application = self.db.query(JobApplication).filter(JobApplication.id == application_id).first()
        if not application:
            return {"status": "error", "message": "Application not found"}

        user = self.db.query(User).filter(User.id == application.user_id).first()
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == application.user_id).first()
        creds = self.db.query(AutoApplyCredential).filter(AutoApplyCredential.user_id == application.user_id).first()

        if not application.tailored_cv or not application.cover_letter:
            self._set_status(application, "requires_intervention",
                             "Materials not prepared. Please generate a Tailored CV and Cover Letter first.")
            return {"status": "intervention", "message": "Materials not ready"}

        url = application.application_url or ""
        if application.job_opportunity_id:
            job = self.db.query(JobOpportunity).filter(JobOpportunity.id == application.job_opportunity_id).first()
            if job:
                url = url or job.application_url

        if not url:
            self._set_status(application, "requires_intervention", "No job application URL found.")
            return {"status": "intervention", "message": "No URL to navigate to"}

        # Normalize LinkedIn collection/search URLs to direct job view URLs
        if "linkedin.com" in url.lower():
            normalized = _normalize_linkedin_url(url)
            if normalized != url:
                logger.info(f"Normalized LinkedIn URL: {url} -> {normalized}")
                url = normalized
                application.application_url = normalized
                self.db.commit()

        ats = _detect_ats(url)
        self._set_status(application, "applying",
                         f"Starting automation for {ats.upper()} platform...",
                         [f"Detected ATS: {ats.upper()}", f"Target URL: {url}"])

        app_data = self._get_app_data(application, user, profile, creds)
        app_data["url"] = url

        result = {"success": False, "intervention": True, "message": "Unknown error", "log": []}

        # Load LinkedIn session cookies + credentials for warm-up fallback
        linkedin_cookies = None
        if ats == "linkedin":
            session_row = self.db.query(LinkedInSession).filter(LinkedInSession.user_id == application.user_id).first()
            if session_row and session_row.cookies_enc:
                try:
                    cookies_json = decrypt_value(session_row.cookies_enc)
                    linkedin_cookies = json.loads(cookies_json)
                    logger.info(f"Retrieved {len(linkedin_cookies)} cookies from LinkedInSession for user {user.email}")
                except Exception as e:
                    logger.warning(f"Could not load LinkedIn cookies: {e}")
            # Also expose the session login credentials so _ensure_linkedin_session can
            # fall back to a full credential login when the injected cookies are stale.
            # These are the credentials from the LinkedIn Connection setup, which always
            # exist if the user has connected LinkedIn — unlike AutoApplyCredential.
            if session_row and session_row.linkedin_email_enc and session_row.linkedin_pw_enc:
                try:
                    app_data["linkedin_session_email"] = decrypt_value(session_row.linkedin_email_enc)
                    app_data["linkedin_session_pw"] = decrypt_value(session_row.linkedin_pw_enc)
                except Exception as e:
                    logger.warning(f"Could not decrypt LinkedIn session credentials for fallback: {e}")

        try:
            # On Windows, FastAPI runs on a SelectorEventLoop which cannot spawn subprocesses
            # (required by Playwright). We run Playwright in a separate thread with its own
            # ProactorEventLoop to avoid the NotImplementedError.
            result = await asyncio.get_event_loop().run_in_executor(
                None, _run_playwright_in_thread, ats, app_data, user.email, linkedin_cookies
            )
        except ImportError:
            result = {
                "success": False,
                "intervention": True,
                "message": "Playwright is not installed. Run: pip install playwright && playwright install chromium",
                "log": ["Playwright not found."],
            }
        except Exception as e:
            logger.exception("Auto-apply runtime error")
            result = {
                "success": False,
                "intervention": True,
                "message": f"Automation error: {str(e)}",
                "log": [f"Error: {str(e)}"],
            }

        # === Handle result ===
        log_lines = result.get("log", [])
        new_account = result.get("new_account")

        if result.get("success"):
            application.status = "applied"
            application.applied_at = datetime.utcnow()
            application.intervention_message = None

            # Polling email for confirmation (Double-lock verification)
            if app_data.get("email_username") and app_data.get("email_password"):
                log_lines.append("Polling email for application confirmation (Double-lock verification)...")
                try:
                    # Allow 15 seconds for confirmation email to arrive
                    await asyncio.sleep(15)
                    verifier = EmailVerificationService(app_data["email_username"], app_data["email_password"])
                    email_verified = await verifier.verify_confirmation(app_data.get("company", ""), app_data.get("job_title", ""))
                    if email_verified:
                        log_lines.append("Email confirmation received! Double-lock success verified.")
                    else:
                        log_lines.append("No confirmation email found yet (this is common, visual success still holds).")
                except Exception as ev_err:
                    log_lines.append(f"Email verification check failed: {ev_err}")
        elif result.get("intervention"):
            application.status = "requires_intervention"
            application.intervention_message = result.get("message", "")
        else:
            application.status = "draft"
            application.intervention_message = result.get("message", "")

        # Append log
        existing_log = json.loads(application.auto_apply_log or "[]")
        existing_log.extend(log_lines)
        application.auto_apply_log = json.dumps(existing_log[-50:])  # Keep last 50 entries

        # Save new account if created
        if new_account:
            account = AutoApplyAccount(
                user_id=application.user_id,
                application_id=application.id,
                platform_name=new_account.get("platform_name", ""),
                platform_url=new_account.get("platform_url", ""),
                username=new_account.get("username", ""),
                password=new_account.get("password", ""),
                notes=new_account.get("notes", ""),
            )
            self.db.add(account)

        self.db.commit()

        return {
            "status": "applied" if result.get("success") else ("intervention" if result.get("intervention") else "error"),
            "message": result.get("message", ""),
            "log": log_lines,
            "new_account_created": bool(new_account),
        }
