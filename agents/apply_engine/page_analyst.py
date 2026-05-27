"""
PageAnalyst — Identifies the current state of a job application page.

Cost strategy (DOM-first):
  1. Extract DOM fields for free (zero LLM calls).
  2. If the DOM is rich enough (>= 2 labeled fields), use MICRO text tier
     to classify the page and plan form assignments — no screenshot needed.
  3. Only escalate to VISION tier when the DOM is sparse/ambiguous
     (e.g. custom React widgets, canvas-based forms, CAPTCHAs).

This means most standard ATS pages (Greenhouse, Lever, Workday) never
trigger a vision call, keeping cost near zero for the analyst step.
"""

from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Any, Dict, List, Optional

from agents.core.base_agent import BaseAgent
from agents.core.llm_bridge import LLMTier


# ─────────────────────────────────────────────────────────────────────────────
# Page-state enum
# ─────────────────────────────────────────────────────────────────────────────

class PageState(str, Enum):
    LOADING          = "loading"
    OVERLAY          = "overlay"          # Cookie banner, privacy notice, modal
    LOGIN            = "login"            # Email + password form
    REGISTER         = "register"         # Account creation form
    EMAIL_VERIFY     = "email_verify"     # "Check your email" screen
    CAPTCHA          = "captcha"          # CAPTCHA challenge
    JOB_DESCRIPTION  = "job_description"  # Landing page with Apply button
    FORM_STEP        = "form_step"        # Multi-step application form
    REVIEW           = "review"           # Review/confirm before submit
    SUCCESS          = "success"          # Application submitted confirmation
    REDIRECT         = "redirect"         # Redirecting to external ATS
    UNKNOWN          = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# PageAnalysis result
# ─────────────────────────────────────────────────────────────────────────────

class PageAnalysis:
    """Result object returned by PageAnalyst.analyse()."""

    def __init__(self, raw: Dict[str, Any], fields: List[Dict[str, Any]]):
        self.state: PageState = PageState(raw.get("state", "unknown"))
        self.confidence: int = raw.get("confidence", 0)
        self.step_label: str = raw.get("step_label", "")         # e.g. "Personal Information"
        self.ats_hint: str = raw.get("ats_hint", "generic")      # "workday", "greenhouse", etc.
        self.overlays: List[str] = raw.get("overlays", [])       # visible overlay types
        self.apply_button_id: Optional[str] = raw.get("apply_button_id")
        self.fields: List[Dict[str, Any]] = fields                # full DOM field list
        self.reasoning: str = raw.get("reasoning", "")
        self._raw = raw

    @property
    def is_form(self) -> bool:
        return self.state in (PageState.FORM_STEP, PageState.LOGIN, PageState.REGISTER, PageState.REVIEW)

    @property
    def needs_vision(self) -> bool:
        return self.confidence < 60

    def __repr__(self) -> str:
        return f"<PageAnalysis state={self.state} conf={self.confidence}% step='{self.step_label}'>"


# ─────────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────────

_DOM_CLASSIFY_PROMPT = """
You are a job-application browser agent. Based on the page URL and the list
of interactive DOM elements below, classify the current page state.

URL: {url}

INTERACTIVE ELEMENTS:
{dom_context}

Classify the page and return ONLY valid JSON:
{{
  "state": "loading|overlay|login|register|email_verify|captcha|job_description|form_step|review|success|redirect|unknown",
  "confidence": 0-100,
  "step_label": "short human label for this step, e.g. 'Personal Information', 'Work Authorization'",
  "ats_hint": "workday|greenhouse|lever|successfactors|smartrecruiters|icims|taleo|jobsch|linkedin|generic",
  "overlays": ["cookie_banner|sign_in_wall|privacy_notice|..."],
  "apply_button_id": "data-cr-id number as string, or null if not visible",
  "reasoning": "one sentence"
}}
"""

_VISION_CLASSIFY_PROMPT = """
You are a job-application browser agent. Analyse this screenshot of a web page
and classify its current state.

URL: {url}
DOM ELEMENTS (partial, may be incomplete for custom widgets):
{dom_context}

Many interactive elements are labeled with red [N] overlays.

Classify the page and return ONLY valid JSON:
{{
  "state": "loading|overlay|login|register|email_verify|captcha|job_description|form_step|review|success|redirect|unknown",
  "confidence": 0-100,
  "step_label": "short human label, e.g. 'Personal Information', 'Work Authorization'",
  "ats_hint": "workday|greenhouse|lever|successfactors|smartrecruiters|icims|taleo|jobsch|linkedin|generic",
  "overlays": ["cookie_banner|sign_in_wall|privacy_notice"],
  "apply_button_id": "data-cr-id number as string, or null",
  "reasoning": "one sentence"
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# PageAnalyst
# ─────────────────────────────────────────────────────────────────────────────

class PageAnalyst(BaseAgent):
    """
    Classifies the current browser page state.

    Usage:
        analyst = PageAnalyst()
        analysis = await analyst.analyse(page)
        if analysis.state == PageState.FORM_STEP:
            ...
    """

    # DOM is considered "rich" if we have at least this many labeled fields
    _DOM_RICH_THRESHOLD = 2

    async def analyse(self, page, force_vision: bool = False) -> PageAnalysis:
        """
        Classify the current page. Returns a PageAnalysis object.

        Steps:
          1. Extract DOM fields (free).
          2. If DOM is rich and not force_vision → text tier (MICRO).
          3. If DOM is sparse or confidence < 60 → vision tier.
        """
        url = page.url

        # Step 1: free DOM extraction — labels elements as side-effect
        fields = await self.extract_dom_fields(page)
        dom_ctx = self.fields_to_context_string(fields)
        dom_is_rich = len(fields) >= self._DOM_RICH_THRESHOLD

        # Step 2: DOM-only classification (cheap)
        if dom_is_rich and not force_vision:
            prompt = _DOM_CLASSIFY_PROMPT.format(url=url, dom_context=dom_ctx)
            raw = await self.llm_text(prompt, LLMTier.MICRO)
            analysis = PageAnalysis(raw, fields)
            self.logger.info(f"PageAnalyst (DOM): {analysis}")

            if not analysis.needs_vision:
                return analysis
            self.logger.info("DOM confidence low — escalating to vision.")

        # Step 3: vision fallback
        await self.label_page_for_vision(page)
        screenshot = await self.screenshot(page)
        prompt = _VISION_CLASSIFY_PROMPT.format(url=url, dom_context=dom_ctx[:2000])
        raw = await self.llm_vision(prompt, screenshot, LLMTier.VISION, dom_context=dom_ctx[:2000])
        analysis = PageAnalysis(raw, fields)
        self.logger.info(f"PageAnalyst (vision): {analysis}")
        return analysis
