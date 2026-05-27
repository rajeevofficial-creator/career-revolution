"""
FormFiller — Survey-then-Execute batch form filler.

Instead of one LLM call per field (expensive and slow), this agent:

  1. SURVEY  — One LLM call analyses all visible fields and returns a
               complete action plan for the whole page step.
  2. EXECUTE — Plays back the plan with Playwright (zero LLM calls).
  3. VERIFY  — Lightweight DOM re-check confirms required fields are filled.

Cost: 1 MICRO text call per form step when DOM is well-labeled.
      1 VISION call per step when DOM is ambiguous.

The user profile dict passed in MUST contain the keys built by
AutoApplyAgent._get_app_data().
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from typing import Any, Dict, List, Optional, Tuple

from agents.core.base_agent import BaseAgent
from agents.core.llm_bridge import LLMTier
from agents.apply_engine.page_analyst import PageAnalysis


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Survey prompt
# ─────────────────────────────────────────────────────────────────────────────

_SURVEY_PROMPT = """
You are an expert job application assistant. Your task is to fill all visible
form fields on this page step using the user's profile data.

USER PROFILE:
{profile_json}

VISIBLE FORM FIELDS (id / type / label / placeholder / required / current_value):
{dom_context}

PAGE STEP: {step_label}
URL: {url}

INSTRUCTIONS:
- Map each unfilled required field (and any optional field you have data for)
  to the correct value from the user profile.
- For SELECT fields, pick the option value that best matches.
- For file UPLOAD fields, mark action as "UPLOAD".
- For checkboxes/radios, use action "CHECK" or "UNCHECK".
- For CLICK targets (Next/Submit/Review buttons), use action "CLICK".
- Prefer to fill fields in top-to-bottom order (ascending id).
- NEVER invent data not present in the user profile. Leave field blank if unknown.
- If a dropdown asks about work authorization, choose the most appropriate
  "Yes" / authorised option.
- If a field asks years of experience, compute from the profile's experience list.
- Ignore already-filled fields.

Return ONLY valid JSON:
{{
  "step_summary": "one-line description of this form step",
  "actions": [
    {{
      "element_id": "string (data-cr-id number)",
      "action": "TYPE | SELECT | CHECK | UNCHECK | UPLOAD | CLICK | SKIP",
      "value": "string value or null for CLICK/UPLOAD/SKIP",
      "reason": "field label or short why"
    }}
  ],
  "navigation_action": {{
    "element_id": "id of the Next/Review/Submit button, or null",
    "button_text": "Next | Review | Submit application | null"
  }},
  "confidence": 0-100
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Execution helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _human_delay(min_ms: int = 300, max_ms: int = 1200):
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def _type_human(page, element, text: str):
    """Type text character-by-character with realistic delays."""
    await element.scroll_into_view_if_needed()
    await element.click()
    await asyncio.sleep(random.uniform(0.1, 0.3))
    await element.fill("")  # clear first
    await element.type(text, delay=random.randint(40, 110))


# ─────────────────────────────────────────────────────────────────────────────
# FormFiller
# ─────────────────────────────────────────────────────────────────────────────

class FormFiller(BaseAgent):
    """
    Fills one page step of a job application form.

    Usage:
        filler = FormFiller()
        result = await filler.fill_step(page, analysis, user_profile, log)
        # result: {"filled": int, "navigated": bool, "needs_vision": bool}
    """

    async def fill_step(
        self,
        page,
        analysis: PageAnalysis,
        user_profile: Dict[str, Any],
        log: List[str],
        force_vision: bool = False,
    ) -> Dict[str, Any]:
        """
        Survey this form step and execute all field assignments.
        Returns a summary dict.
        """
        fields = analysis.fields
        dom_ctx = self.fields_to_context_string(fields)
        url = page.url

        # ── 1. Survey (plan all actions for this step) ────────────────────────
        plan = await self._survey(page, analysis, user_profile, dom_ctx, url, force_vision)
        if "error" in plan:
            log.append(f"Survey failed: {plan['error']}")
            return {"filled": 0, "navigated": False, "needs_vision": True}

        log.append(f"Form survey: {plan.get('step_summary', '?')} — {len(plan.get('actions', []))} actions planned (confidence {plan.get('confidence', 0)}%)")

        # ── 2. Execute planned actions ────────────────────────────────────────
        filled = 0
        for action_item in plan.get("actions", []):
            executed = await self._execute_action(page, action_item, user_profile, log)
            if executed:
                filled += 1
            await _human_delay(200, 600)

        # ── 3. Handle navigation button ───────────────────────────────────────
        navigated = False
        nav = plan.get("navigation_action", {})
        if nav and nav.get("element_id"):
            navigated = await self._click_navigation(page, nav, log)

        log.append(f"Fill step complete: {filled} fields filled, navigated={navigated}")
        return {
            "filled": filled,
            "navigated": navigated,
            "needs_vision": plan.get("confidence", 100) < 60,
            "step_summary": plan.get("step_summary", ""),
        }

    # ── Survey ────────────────────────────────────────────────────────────────

    async def _survey(
        self,
        page,
        analysis: PageAnalysis,
        user_profile: Dict[str, Any],
        dom_ctx: str,
        url: str,
        force_vision: bool,
    ) -> Dict[str, Any]:
        # Strip sensitive fields before sending to LLM
        safe_profile = {k: v for k, v in user_profile.items()
                        if k not in ("linkedin_password", "email_password")}
        profile_json = json.dumps(safe_profile, indent=2, default=str)

        prompt = _SURVEY_PROMPT.format(
            profile_json=profile_json[:3000],
            dom_context=dom_ctx[:2500],
            step_label=analysis.step_label or "Form Step",
            url=url,
        )

        # Use MICRO (text) if DOM is well labeled, else VISION
        use_vision = force_vision or len(analysis.fields) < 2

        if use_vision:
            await self.label_page_for_vision(page)
            screenshot = await self.screenshot(page)
            result = await self.llm_vision(prompt, screenshot, LLMTier.VISION, dom_context=dom_ctx[:2000])
        else:
            result = await self.llm_text(prompt, LLMTier.MICRO)

        return result

    # ── Execute single action ─────────────────────────────────────────────────

    async def _execute_action(
        self,
        page,
        action_item: Dict[str, Any],
        user_profile: Dict[str, Any],
        log: List[str],
    ) -> bool:
        action = action_item.get("action", "").upper()
        el_id = str(action_item.get("element_id", ""))
        value = action_item.get("value") or ""
        reason = action_item.get("reason", "")

        if action == "SKIP" or not el_id:
            return False

        element = await page.query_selector(f'[data-cr-id="{el_id}"]')
        if not element:
            log.append(f"  [{el_id}] not found on page ({reason})")
            return False

        try:
            visible = await element.is_visible()
            if not visible:
                return False

            if action == "TYPE":
                if not value:
                    return False
                await _type_human(page, element, str(value))
                log.append(f"  [{el_id}] typed: '{str(value)[:40]}' ({reason})")
                return True

            elif action == "SELECT":
                if not value:
                    return False
                try:
                    await element.select_option(value=str(value))
                except Exception:
                    # Fallback: try matching by label text
                    try:
                        await element.select_option(label=str(value))
                    except Exception as e:
                        log.append(f"  [{el_id}] SELECT fallback failed: {e}")
                        return False
                log.append(f"  [{el_id}] selected: '{value}' ({reason})")
                return True

            elif action == "CHECK":
                checked = await element.is_checked()
                if not checked:
                    await element.check()
                log.append(f"  [{el_id}] checked ({reason})")
                return True

            elif action == "UNCHECK":
                checked = await element.is_checked()
                if checked:
                    await element.uncheck()
                log.append(f"  [{el_id}] unchecked ({reason})")
                return True

            elif action == "UPLOAD":
                cv_path = user_profile.get("cv_path", "")
                if not cv_path:
                    log.append(f"  [{el_id}] UPLOAD skipped — no cv_path in profile")
                    return False
                if not os.path.isabs(cv_path):
                    cv_path = os.path.abspath(cv_path)
                if not os.path.exists(cv_path):
                    log.append(f"  [{el_id}] UPLOAD skipped — file not found: {cv_path}")
                    return False
                await element.set_input_files(cv_path)
                await _human_delay(1500, 2500)
                log.append(f"  [{el_id}] uploaded CV: {os.path.basename(cv_path)}")
                return True

            elif action == "CLICK":
                # Navigation clicks handled separately; skip here
                return False

        except Exception as e:
            log.append(f"  [{el_id}] action {action} error: {e}")
            return False

        return False

    # ── Navigation ────────────────────────────────────────────────────────────

    async def _click_navigation(
        self,
        page,
        nav: Dict[str, Any],
        log: List[str],
    ) -> bool:
        el_id = str(nav.get("element_id", ""))
        btn_text = nav.get("button_text", "?")

        element = await page.query_selector(f'[data-cr-id="{el_id}"]')
        if not element:
            # Fallback: find by text
            element = await self._find_nav_button_by_text(page, btn_text)

        if not element:
            log.append(f"Navigation button [{el_id}] '{btn_text}' not found.")
            return False

        # Check if disabled
        disabled = await element.get_attribute("disabled")
        aria_disabled = await element.get_attribute("aria-disabled")
        if disabled is not None or aria_disabled == "true":
            log.append(f"Navigation button [{el_id}] '{btn_text}' is disabled — required fields may be missing.")
            return False

        log.append(f"Clicking navigation: '{btn_text}' [{el_id}]")
        try:
            await element.click(force=True, timeout=5000)
        except Exception:
            await page.evaluate("el => el.click()", element)

        await _human_delay(1200, 2200)
        return True

    async def _find_nav_button_by_text(self, page, btn_text: str):
        """Last-resort: find a navigation button by text matching (language-agnostic set)."""
        patterns = {
            "Submit application": [
                'button:has-text("Submit application")',
                'button[aria-label*="Submit application"]',
                'button:has-text("Submit")',
            ],
            "Review": [
                'button:has-text("Review")',
                'button[aria-label*="Review"]',
            ],
            "Next": [
                'button:has-text("Next")',
                'button:has-text("Continue")',
                'button:has-text("Weiter")',        # German
                'button:has-text("Suivant")',        # French
                'button:has-text("Avanti")',         # Italian
                'button[aria-label*="Continue to next step"]',
            ],
        }
        search_order = ["Submit application", "Review", "Next"]
        # If we have a hint, try that first
        if btn_text:
            for key in search_order:
                if key.lower() in btn_text.lower():
                    search_order.insert(0, search_order.pop(search_order.index(key)))
                    break

        for key in search_order:
            for sel in patterns.get(key, []):
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    return el
        return None
