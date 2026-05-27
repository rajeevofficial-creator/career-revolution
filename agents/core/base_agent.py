"""
BaseAgent — shared foundation for all Career Revolution agents.

Every specialist agent (PageAnalyst, FormFiller, JobSearchAgent, etc.)
inherits from this class and gets:
  - A configured LLMBridge (provider-agnostic)
  - A structured logger
  - A lightweight cost/call counter for the session
  - Helper: dom_context_from_page(page) — free DOM extraction, no LLM call

Design goal: keep this class thin. Domain logic belongs in subclasses.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from agents.core.llm_bridge import LLMBridge, LLMTier, build_bridge_from_settings


# ─────────────────────────────────────────────────────────────────────────────
# JS: extract ALL interactive elements with semantic labels (free, no LLM)
# ─────────────────────────────────────────────────────────────────────────────

_DOM_EXTRACT_JS = """
() => {
    const sel = [
        'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
        'select',
        'textarea',
        '[role="combobox"]',
        '[role="radio"]',
        '[role="checkbox"]',
        '[contenteditable="true"]',
        'button:not([data-cr-nav])',
        'a[role="button"]',
        'input[type="submit"]',
        'input[type="button"]',
    ].join(', ');

    const getLabel = (el) => {
        // 1. Explicit label[for]
        if (el.id) {
            const lbl = document.querySelector('label[for="' + el.id + '"]');
            if (lbl) return lbl.textContent.trim();
        }
        // 2. aria-label
        const aria = el.getAttribute('aria-label');
        if (aria) return aria.trim();
        // 3. aria-labelledby
        const lblId = el.getAttribute('aria-labelledby');
        if (lblId) {
            const lblEl = document.getElementById(lblId);
            if (lblEl) return lblEl.textContent.trim();
        }
        // 4. Nearest ancestor label
        let p = el.parentElement;
        for (let i = 0; i < 4 && p; i++, p = p.parentElement) {
            if (p.tagName === 'LABEL') return p.textContent.replace(el.textContent, '').trim();
        }
        // 5. Placeholder / name
        return el.placeholder || el.name || '';
    };

    const fields = [];
    let count = 0;
    document.querySelectorAll(sel).forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        if (rect.top < -50 || rect.top > window.innerHeight + 50) return;

        count++;
        el.setAttribute('data-cr-id', count);

        fields.push({
            id:          count,
            tag:         el.tagName.toLowerCase(),
            type:        el.type || el.getAttribute('role') || el.tagName.toLowerCase(),
            label:       getLabel(el),
            placeholder: el.placeholder || '',
            name:        el.name || '',
            value:       el.value ? '(filled)' : '',
            required:    el.required || el.getAttribute('aria-required') === 'true',
            text:        (el.innerText || el.textContent || '').trim().slice(0, 80),
        });
    });
    return JSON.stringify(fields);
}
"""

# Companion: inject coloured overlays for vision-assisted recovery
_LABEL_OVERLAY_JS = """
() => {
    document.querySelectorAll('.cr-vision-label').forEach(e => e.remove());
    let shown = 0;
    document.querySelectorAll('[data-cr-id]').forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        const id = el.getAttribute('data-cr-id');
        const div = document.createElement('div');
        div.className = 'cr-vision-label';
        div.innerText = '[' + id + ']';
        div.style.cssText = [
            'position:fixed',
            'top:' + rect.top + 'px',
            'left:' + rect.left + 'px',
            'background:rgba(220,38,38,0.85)',
            'color:#fff',
            'padding:1px 4px',
            'font-size:11px',
            'font-weight:700',
            'z-index:2147483647',
            'pointer-events:none',
            'border-radius:3px',
            'line-height:1.4',
        ].join(';');
        document.body.appendChild(div);
        shown++;
    });
    return shown;
}
"""

_REMOVE_OVERLAY_JS = "document.querySelectorAll('.cr-vision-label').forEach(e => e.remove())"


# ─────────────────────────────────────────────────────────────────────────────
# BaseAgent
# ─────────────────────────────────────────────────────────────────────────────

class BaseAgent:
    """
    Inherit from this to build a specialist agent.
    Subclasses typically override only their core logic methods.

    Pass `provider="claude"` to override the system default for a specific run.
    """

    def __init__(self, llm: Optional[LLMBridge] = None, provider: Optional[str] = None):
        if llm:
            self.llm = llm
        elif provider:
            from app.config import settings
            self.llm = LLMBridge(
                provider=provider,
                gemini_api_key=getattr(settings, "gemini_api_key", None),
                anthropic_api_key=getattr(settings, "anthropic_api_key", None),
            )
        else:
            self.llm = build_bridge_from_settings()
        self.logger = logging.getLogger(self.__class__.__name__)
        # Lightweight session counters for cost awareness
        self._calls: Dict[LLMTier, int] = {t: 0 for t in LLMTier}

    # ── LLM call wrappers (increment counters) ────────────────────────────────

    async def llm_text(self, prompt: str, tier: LLMTier = LLMTier.MICRO) -> Dict[str, Any]:
        self._calls[tier] += 1
        return await self.llm.text(prompt, tier)

    async def llm_vision(
        self,
        prompt: str,
        image_bytes: bytes,
        tier: LLMTier = LLMTier.VISION,
        dom_context: str = "",
    ) -> Dict[str, Any]:
        self._calls[tier] += 1
        return await self.llm.vision(prompt, image_bytes, tier, dom_context)

    def call_summary(self) -> Dict[str, int]:
        """Return LLM call counts by tier for this agent's session."""
        return {tier.value: count for tier, count in self._calls.items() if count > 0}

    # ── DOM helpers ───────────────────────────────────────────────────────────

    async def extract_dom_fields(self, page) -> List[Dict[str, Any]]:
        """
        Extract all interactive elements from the page DOM.
        Labels each element with data-cr-id so vision can reference them.
        Returns a list of field dicts. Zero LLM calls.
        """
        try:
            raw = await page.evaluate(_DOM_EXTRACT_JS)
            fields = json.loads(raw)
            self.logger.debug(f"DOM extract: {len(fields)} interactive elements found")
            return fields
        except Exception as e:
            self.logger.warning(f"DOM extract failed: {e}")
            return []

    async def label_page_for_vision(self, page) -> int:
        """
        Inject coloured [N] overlays on every data-cr-id element.
        Returns count of overlays shown. Call extract_dom_fields first.
        """
        try:
            count = await page.evaluate(_LABEL_OVERLAY_JS)
            await asyncio.sleep(0.3)
            return count
        except Exception as e:
            self.logger.warning(f"Label overlay failed: {e}")
            return 0

    async def remove_labels(self, page):
        """Clean up vision overlay labels."""
        try:
            await page.evaluate(_REMOVE_OVERLAY_JS)
        except Exception:
            pass

    def fields_to_context_string(self, fields: List[Dict[str, Any]]) -> str:
        """
        Render DOM fields as a compact text block for LLM prompts.
        Example line: [3] input/text  "First name"  placeholder="First name"  required
        """
        lines = []
        for f in fields:
            req = " required" if f.get("required") else ""
            val = "  (already filled)" if f.get("value") else ""
            lines.append(
                f"[{f['id']}] {f['tag']}/{f['type']}  \"{f['label'] or f['placeholder'] or f['name']}\""
                f"  placeholder=\"{f['placeholder']}\"{req}{val}"
            )
        return "\n".join(lines) if lines else "(no interactive elements found)"

    # ── Screenshot helper ─────────────────────────────────────────────────────

    async def screenshot(self, page) -> bytes:
        """Take a viewport screenshot. Auto-removes labels first."""
        await self.remove_labels(page)
        return await page.screenshot(type="png", full_page=False)
