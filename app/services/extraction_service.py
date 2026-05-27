"""
Extraction Service — converts URLs into clean Markdown.
Returns structured diagnostics so callers can surface clear errors to the user.
"""

import logging
import re
import requests
import asyncio
from typing import Optional, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

# Phrases that indicate the scraped page is an auth-wall / login page rather than content
_AUTH_WALL_PHRASES = [
    "sign in to", "log in to", "create an account", "join now to",
    "please log in", "you must be logged in", "sign up to continue",
    "authwall", "join linkedin", "join now", "we need you to verify",
    "please sign in", "session has expired",
]

# Phrases that indicate a 404 / expired posting
_NOT_FOUND_PHRASES = [
    "no longer accepting applications", "this job is no longer",
    "job not found", "position has been filled", "posting has expired",
    "page not found", "404", "this job has been closed",
]


def _classify_content(url: str, content: str) -> Dict[str, Any]:
    """
    Inspect scraped content and return a diagnosis dict:
      status  : "success" | "auth_required" | "not_found" | "too_short" | "empty"
      content : the raw content (may be None)
      reason  : human-readable explanation suitable for displaying to the user
    """
    if not content:
        return {
            "status": "empty",
            "content": None,
            "reason": "The scraper returned no content from this URL.",
        }

    lower = content.lower()

    # Auth-wall detection
    for phrase in _AUTH_WALL_PHRASES:
        if phrase in lower:
            if "linkedin.com" in url.lower():
                return {
                    "status": "auth_required",
                    "content": None,
                    "reason": (
                        "LinkedIn job descriptions require you to be logged in — "
                        "they cannot be accessed automatically. "
                        "Please open the job posting, copy the description, and paste it below."
                    ),
                }
            return {
                "status": "auth_required",
                "content": None,
                "reason": (
                    "This job page requires a login to view the description — "
                    "it cannot be scraped automatically. "
                    "Please open the link, copy the job description, and paste it below."
                ),
            }

    # 404 / expired detection
    for phrase in _NOT_FOUND_PHRASES:
        if phrase in lower:
            return {
                "status": "not_found",
                "content": None,
                "reason": (
                    "This job posting appears to have expired or been removed. "
                    "Please verify the link is still active, or paste the description if you have it."
                ),
            }

    # Content too short to be a real job description
    if len(content.strip()) < 200:
        return {
            "status": "too_short",
            "content": None,
            "reason": (
                f"The page returned only {len(content.strip())} characters — "
                "not enough to be a full job description. "
                "Please paste the job description manually below."
            ),
        }

    return {"status": "success", "content": content, "reason": ""}


class ExtractionService:
    """Service for extracting clean Markdown content from URLs."""

    def __init__(self):
        self.firecrawl_key = settings.firecrawl_api_key
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    async def extract_with_diagnosis(self, url: str) -> Dict[str, Any]:
        """
        Fetch content from a URL and return a structured diagnosis dict:
          status  : "success" | "auth_required" | "not_found" | "too_short" | "empty" | "error"
          content : extracted Markdown text (only when status == "success")
          reason  : user-facing explanation of the problem (empty on success)
        """
        raw = None

        # Try Firecrawl first if a key is configured
        if self.firecrawl_key:
            raw = await self._fetch_firecrawl(url)

        # Fall back to Jina Reader
        if not raw:
            raw = await self._fetch_jina(url)

        if raw is None:
            return {
                "status": "error",
                "content": None,
                "reason": (
                    "Could not reach this URL — it may be down, blocked, or require a VPN. "
                    "Please paste the job description manually below."
                ),
            }

        return _classify_content(url, raw)

    # Keep the original method for callers that don't need diagnosis
    async def extract_markdown(self, url: str) -> Optional[str]:
        result = await self.extract_with_diagnosis(url)
        return result["content"] if result["status"] == "success" else None

    async def _fetch_firecrawl(self, url: str) -> Optional[str]:
        api_url = "https://api.firecrawl.dev/v0/scrape"
        payload = {
            "url": url,
            "pageOptions": {"onlyMainContent": True},
            "wait_for": 2000,
        }
        headers = {
            "Authorization": f"Bearer {self.firecrawl_key}",
            "Content-Type": "application/json",
        }
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.post(api_url, json=payload, headers=headers, timeout=30)
            )
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("content", "")
        except Exception as e:
            logger.error(f"Firecrawl failed: {e}")
        return None

    async def _fetch_jina(self, url: str) -> Optional[str]:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {
            "User-Agent": self.user_agent,
            "X-With-Generated-Alt": "true",
        }
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(jina_url, headers=headers, timeout=20)
            )
            if resp.status_code == 200:
                return resp.text
            # Return the body even on non-200 — it may contain auth-wall text
            # useful for _classify_content to identify the real failure reason
            logger.warning(f"Jina Reader returned HTTP {resp.status_code} for {url}")
            if resp.text:
                return resp.text
        except Exception as e:
            logger.error(f"Jina Reader failed: {e}")
        return None
