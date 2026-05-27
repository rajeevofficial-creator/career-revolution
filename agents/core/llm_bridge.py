"""
LLM Bridge — Provider-agnostic interface for all agent LLM calls.

Supports Gemini and Claude. Users configure their preferred provider
via LLM_PROVIDER env var ("gemini" | "claude").

Cost tiers map to model sizes:
  MICRO  — text-only, cheapest  → Gemini Flash-Lite  / Claude Haiku
  VISION — screenshot + DOM     → Gemini Flash       / Claude Sonnet
  POWER  — complex planning     → Gemini Pro         / Claude Opus

Rule of thumb:
  Use MICRO whenever you have good DOM context and don't need vision.
  Use VISION for page analysis and form survey when DOM is ambiguous.
  Use POWER sparingly — only for multi-document strategic planning.
"""

import base64
import json
import logging
import re
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Tier enum
# ─────────────────────────────────────────────────────────────────────────────

class LLMTier(str, Enum):
    MICRO  = "micro"   # DOM-only, text tasks — lowest cost
    VISION = "vision"  # Screenshot + DOM context — standard cost
    POWER  = "power"   # Complex multi-step planning — use sparingly


# ─────────────────────────────────────────────────────────────────────────────
# Model registry
# ─────────────────────────────────────────────────────────────────────────────

_GEMINI_MODELS = {
    LLMTier.MICRO:  ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"],
    LLMTier.VISION: ["gemini-3.5-flash", "gemini-2.5-flash",      "gemini-2.5-pro"],
    LLMTier.POWER:  ["gemini-2.5-pro",   "gemini-3.5-flash"],
}

_CLAUDE_MODELS = {
    LLMTier.MICRO:  "claude-haiku-4-5-20251001",
    LLMTier.VISION: "claude-sonnet-4-6",
    LLMTier.POWER:  "claude-opus-4-7",
}


# ─────────────────────────────────────────────────────────────────────────────
# JSON parsing helper (shared by both providers)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json(text: str) -> Dict[str, Any]:
    """Extract and parse the first JSON object or array from a text response."""
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = text.rstrip("`").strip()

    obj_pos = text.find('{')
    arr_pos = text.find('[')

    # Order pairs so we try the outermost bracket type first
    if arr_pos != -1 and (obj_pos == -1 or arr_pos < obj_pos):
        pairs = [('[', ']'), ('{', '}')]
    else:
        pairs = [('{', '}'), ('[', ']')]

    for start_char, end_char in pairs:
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break

    logger.warning(f"Could not parse JSON from response: {text[:200]}")
    return {"error": "Could not parse JSON", "raw": text[:500]}


# ─────────────────────────────────────────────────────────────────────────────
# LLMBridge
# ─────────────────────────────────────────────────────────────────────────────

class LLMBridge:
    """
    Provider-agnostic LLM interface used by all agents.

    Usage:
        bridge = LLMBridge(provider="gemini", gemini_api_key="...")
        result = await bridge.text("Return JSON: {...}", tier=LLMTier.MICRO)
        result = await bridge.vision("Describe this form", screenshot_bytes, dom_ctx="fields: ...")
    """

    def __init__(
        self,
        provider: str = "gemini",
        gemini_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        self.provider = provider.lower()
        self._gemini_key = gemini_api_key
        self._anthropic_key = anthropic_api_key
        self._gemini_models: Dict[LLMTier, Any] = {}
        self._anthropic_client = None
        self._setup()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _setup(self):
        if self.provider == "gemini" and self._gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._gemini_key)
                for tier, model_list in _GEMINI_MODELS.items():
                    for model_name in model_list:
                        try:
                            self._gemini_models[tier] = genai.GenerativeModel(model_name)
                            break
                        except Exception:
                            continue
                logger.info(f"LLMBridge: Gemini ready — {[str(m.model_name) for m in self._gemini_models.values()]}")
            except ImportError:
                logger.warning("LLMBridge: google-generativeai not installed.")

        elif self.provider == "claude" and self._anthropic_key:
            try:
                import anthropic
                self._anthropic_client = anthropic.Anthropic(api_key=self._anthropic_key)
                logger.info("LLMBridge: Claude ready.")
            except ImportError:
                logger.warning("LLMBridge: anthropic SDK not installed.")

        else:
            logger.warning(f"LLMBridge: No API key for provider '{self.provider}'. LLM calls will fail.")

    def is_available(self) -> bool:
        if self.provider == "gemini":
            return bool(self._gemini_models)
        return self._anthropic_client is not None

    # ── Public API ────────────────────────────────────────────────────────────

    async def text(self, prompt: str, tier: LLMTier = LLMTier.MICRO) -> Dict[str, Any]:
        """
        Text-only call. No image. Uses MICRO tier by default (cheapest).
        Always returns a parsed dict.
        """
        if not self.is_available():
            return {"error": f"LLMBridge not configured for provider '{self.provider}'"}
        if self.provider == "gemini":
            return await self._gemini_text(prompt, tier)
        return await self._claude_text(prompt, tier)

    async def vision(
        self,
        prompt: str,
        image_bytes: bytes,
        tier: LLMTier = LLMTier.VISION,
        dom_context: str = "",
    ) -> Dict[str, Any]:
        """
        Vision call. Pass a PNG screenshot and optional DOM context string.
        DOM context is prepended to the prompt so both providers get it.
        Uses VISION tier by default.
        """
        if not self.is_available():
            return {"error": f"LLMBridge not configured for provider '{self.provider}'"}

        full_prompt = f"{dom_context}\n\n{prompt}" if dom_context else prompt

        if self.provider == "gemini":
            return await self._gemini_vision(full_prompt, image_bytes, tier)
        return await self._claude_vision(prompt, image_bytes, tier, dom_context)

    # ── Gemini implementations ────────────────────────────────────────────────

    async def _gemini_text(self, prompt: str, tier: LLMTier) -> Dict[str, Any]:
        model = self._gemini_models.get(tier) or self._gemini_models.get(LLMTier.MICRO)
        if not model:
            return {"error": "No Gemini model available"}
        try:
            response = model.generate_content(prompt)
            return _parse_json(response.text)
        except Exception as e:
            logger.error(f"Gemini text ({tier}): {e}")
            # Cascade to VISION model on quota/404
            if tier == LLMTier.MICRO:
                fallback = self._gemini_models.get(LLMTier.VISION)
                if fallback:
                    try:
                        response = fallback.generate_content(prompt)
                        return _parse_json(response.text)
                    except Exception as e2:
                        logger.error(f"Gemini VISION fallback: {e2}")
            return {"error": str(e)}

    async def _gemini_vision(self, prompt: str, image_bytes: bytes, tier: LLMTier) -> Dict[str, Any]:
        model = (
            self._gemini_models.get(tier)
            or self._gemini_models.get(LLMTier.VISION)
            or self._gemini_models.get(LLMTier.MICRO)
        )
        if not model:
            return {"error": "No Gemini model available"}
        try:
            response = model.generate_content([
                prompt,
                {"mime_type": "image/png", "data": image_bytes},
            ])
            return _parse_json(response.text)
        except Exception as e:
            logger.error(f"Gemini vision ({tier}): {e}")
            return {"error": str(e)}

    # ── Claude implementations ────────────────────────────────────────────────

    async def _claude_text(self, prompt: str, tier: LLMTier) -> Dict[str, Any]:
        if not self._anthropic_client:
            return {"error": "Anthropic client not initialised"}
        model = _CLAUDE_MODELS[tier]
        try:
            resp = self._anthropic_client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            return _parse_json(resp.content[0].text)
        except Exception as e:
            logger.error(f"Claude text ({tier} / {model}): {e}")
            return {"error": str(e)}

    async def _claude_vision(
        self,
        prompt: str,
        image_bytes: bytes,
        tier: LLMTier,
        dom_context: str = "",
    ) -> Dict[str, Any]:
        if not self._anthropic_client:
            return {"error": "Anthropic client not initialised"}
        model = _CLAUDE_MODELS[tier]
        try:
            content: list = []
            if dom_context:
                content.append({"type": "text", "text": f"DOM CONTEXT:\n{dom_context}\n"})
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(image_bytes).decode(),
                },
            })
            content.append({"type": "text", "text": prompt})

            resp = self._anthropic_client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": content}],
            )
            return _parse_json(resp.content[0].text)
        except Exception as e:
            logger.error(f"Claude vision ({tier} / {model}): {e}")
            return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Factory — builds a bridge from app settings
# ─────────────────────────────────────────────────────────────────────────────

def build_bridge_from_settings() -> LLMBridge:
    """Convenience factory that reads app/config.py settings."""
    from app.config import settings
    return LLMBridge(
        provider=getattr(settings, "llm_provider", "gemini"),
        gemini_api_key=getattr(settings, "gemini_api_key", None),
        anthropic_api_key=getattr(settings, "anthropic_api_key", None),
    )
