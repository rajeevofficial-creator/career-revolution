"""
Source Discovery Service using Google Gemini.
Identifies high-quality job portals and boutique recruiters tailored to the user.
"""

import json
import logging
from typing import Dict, List, Any
from app.services.llm_analysis import LLMAnalysisService

logger = logging.getLogger(__name__)

class SourceDiscoveryService:
    """Service for discovering job sources (portals, agencies) via LLM."""

    def __init__(self, llm_service: LLMAnalysisService):
        self.llm = llm_service

    async def discover_sources(self, location: str, industry: str) -> List[Dict[str, Any]]:
        """
        Ask LLM to identify top job portals, boutique recruiters, and company career
        pages specialized for a specific location and industry.
        """
        if not self.llm.is_available():
            logger.warning("LLM service not available for source discovery. Falling back to seed data.")
            return self._get_default_sources(location, industry)

        # Industry context: "General" means the user has no specific preference — use it
        # only for recruiter/company targeting, not for portals (portals cover all industries).
        industry_ctx = industry if industry and industry.lower() not in ("general", "") else None

        prompt = f"""
You are a senior career consultant with deep knowledge of the job market in {location}.

Compile a comprehensive list of 50+ high-quality job search sources for {location}.
The target candidate works in: {industry_ctx or "a broad range of industries"}.

Include sources across ALL five categories below. Each category has different industry scope rules — follow them strictly.

---
1. **standard_portal** (10+ entries)
   Scope: ALL industries — do NOT limit to {industry_ctx or "any one field"}.
   Major national job boards and aggregators widely used in {location}.
   Provide the most direct search URL (e.g. with a location filter pre-applied).

2. **global_with_local** (5+ entries)
   Scope: ALL industries.
   Global platforms (LinkedIn, Indeed, Glassdoor, Monster) with a {location}-specific search URL.
   Always include the localised URL — e.g. LinkedIn with the correct geoId, Indeed with the local domain.

3. **boutique_recruiter** (10+ entries)
   Scope: Specialised in {industry_ctx or "multiple sectors"} OR in {location}'s key industries.
   Recruitment agencies and headhunters based in or actively serving {location}.
   Include mid-size and niche firms — not just the global giants.

4. **company_career_page** (20+ entries)
   Scope: Major employers in {location} — across ALL sectors, not just {industry_ctx or "one field"}.
   Include top employers by headcount, top tech companies, top pharma/life sciences, top finance/banking, top manufacturing/engineering, and any industry leaders headquartered there.
   For each company, use the country-specific careers URL if one exists (e.g. containing '/{location[:2].lower()}/', '/country-name/', '?facetCountry={location[:2].upper()}', or '?country={location}').
   Do NOT use the company homepage — go directly to the careers/jobs listing page.

5. **government_portal** (5+ entries)
   Scope: ALL industries — public sector jobs at national, cantonal/state, and city level.
   Include official employment portals, civil service career sites, and municipal job boards for {location}.

---
Guidelines:
- All sources must be real and currently active.
- quality_score: 0–100 reflecting how effective this source is for job-seekers in {location}.
- Tags: include the country, source type keywords, and relevant sectors/industries.

Return ONLY a valid JSON array (no markdown, no explanation):
[
    {{
        "name": "Name of the source",
        "url": "Direct URL to the jobs listing page",
        "source_type": "standard_portal|global_with_local|boutique_recruiter|company_career_page|government_portal",
        "industry": "Primary industry focus (use 'General' for all-industry portals)",
        "sector": "Broader sector (e.g., Finance, Life Sciences, Tech, Public Sector, General)",
        "reasoning": "Why this is valuable for job-seekers in {location}",
        "quality_score": 75,
        "tags": ["{location}", "relevant", "keywords"]
    }}
]
"""

        try:
            response = await self.llm._get_gemini_response(prompt)
            if isinstance(response, list) and len(response) > 0:
                logger.info(f"LLM discovered {len(response)} sources for {location}/{industry}")
                return response
            elif isinstance(response, dict) and "error" in response:
                logger.error(f"LLM error in source discovery: {response['error']}")
                return self._get_default_sources(location, industry)
            else:
                logger.warning(f"Unexpected LLM response type: {type(response)}")
                return self._get_default_sources(location, industry)
        except Exception as e:
            logger.error(f"Error in source discovery: {e}")
            return self._get_default_sources(location, industry)

    async def discover_career_url_by_name(self, company_name: str, country: str) -> str | None:
        """
        Ask the LLM to find the official careers/jobs page URL for a company,
        given only its name and country. Used for CSV-imported companies that
        have no URL stored.

        Returns a verified URL or None if nothing usable is found.
        """
        prompt = f"""
You are a career website expert with up-to-date knowledge of corporate job portals.

Find the official careers/jobs listing page URL for this company:

Company: {company_name}
Country: {country}

Requirements:
- Return the URL of the page that shows MULTIPLE job openings (not homepage, not a single job posting).
- For global companies, prefer the {country}-specific URL where available (e.g. filtered by country/region).
- If the company uses an ATS (Workday, Greenhouse, Lever, SAP SuccessFactors, SmartRecruiters),
  return the direct ATS URL. Do NOT guess Workday country GUIDs — use facetCountry=<2-letter-ISO> if known.
- If you are not confident about the exact URL, return the most direct careers listing page you know.
- Return ONLY a valid JSON object — no markdown, no explanation.

{{"career_url": "https://..."}}
"""
        try:
            response = await self.llm._get_gemini_response(prompt)
            if isinstance(response, dict):
                url = response.get("career_url", "").strip()
                if url and url.startswith("http"):
                    if await self._http_verify_url(url):
                        logger.info(f"Discovered career URL for '{company_name}': {url}")
                        return url
                    else:
                        logger.warning(f"LLM career URL did not resolve for '{company_name}': {url}")
        except Exception as e:
            logger.error(f"discover_career_url_by_name failed for '{company_name}': {e}")
        return None

    async def vet_company_url(self, company_url: str, country: str = None) -> str:
        """
        Find the exact job-listing page for the target country.

        Three-phase approach (fastest-first):
        1. HTTP GET the page and look for country-specific links in the HTML.
        2. Ask the LLM for the country-specific jobs URL.
        3. HTTP HEAD-verify the LLM suggestion actually exists.

        Returns the best URL found (original if all phases fail).
        Use visual_validate_source() separately to do a full Playwright+Vision check.
        """
        country = country or "Switzerland"

        # Phase 1 — scrape HTML for a country-specific link
        scraped = await self._scrape_for_country_url(company_url, country)
        if scraped:
            logger.info(f"Scraped country-specific URL for {company_url}: {scraped}")
            return scraped

        # Phase 2 — ask LLM for the country-specific jobs URL
        llm_url = await self._llm_suggest_country_url(company_url, country)
        if llm_url and llm_url != company_url:
            # Phase 3 — verify the LLM suggestion actually resolves
            if await self._http_verify_url(llm_url):
                logger.info(f"LLM-suggested URL verified for {company_url}: {llm_url}")
                return llm_url
            else:
                logger.warning(f"LLM suggested URL did not resolve: {llm_url} — keeping original")

        return company_url

    async def visual_validate_source(self, url: str, country: str = "Switzerland") -> Dict[str, Any]:
        """
        Use Playwright to render the page (handles JS-heavy SPAs) and Gemini Vision to
        visually confirm the page shows actual job listings for the target country.

        Returns a dict with:
            valid       — bool|None: True if shows job listings; None on API/render errors
            country_ok  — bool: True if listings appear country-specific
            job_count   — int or None: estimated visible jobs on page
            confidence  — "high"|"medium"|"low"
            notes       — str: LLM explanation
            screenshot  — bytes: PNG screenshot (for debugging)
        """
        import asyncio

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed — skipping visual validation.")
            return {"valid": None, "notes": "Playwright not available"}

        screenshot_bytes = None
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                    timezone_id="Europe/Zurich",
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    },
                )
                # Mask navigator.webdriver to reduce bot-detection false positives
                await context.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                except Exception:
                    # networkidle timeout is OK — page may still have content
                    pass
                # Give JS-heavy SPAs time to render
                await asyncio.sleep(3)

                # Dismiss common cookie/consent banners before screenshotting
                consent_selectors = [
                    # Text-based buttons (case-insensitive via :text-is or contains)
                    "button:has-text('Accept all')",
                    "button:has-text('Accept All')",
                    "button:has-text('Accept')",
                    "button:has-text('Akzeptieren')",   # German
                    "button:has-text('Accepter')",      # French
                    "button:has-text('Accetta')",       # Italian
                    "button:has-text('Alle akzeptieren')",
                    "button:has-text('Tout accepter')",
                    "button:has-text('Allow all')",
                    "button:has-text('Allow All')",
                    "button:has-text('I agree')",
                    "button:has-text('OK')",
                    # ID/class-based selectors used by common CMP vendors
                    "#onetrust-accept-btn-handler",
                    "#CybotCookiebotDialogBodyButtonAccept",
                    "[data-testid='cookie-accept']",
                    ".cookie-accept",
                    ".js-accept-cookies",
                ]
                for sel in consent_selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=800):
                            await btn.click(timeout=800)
                            await asyncio.sleep(1)
                            break
                    except Exception:
                        pass

                # Scroll to reveal job cards that load below the fold
                try:
                    await page.evaluate("window.scrollTo(0, 500)")
                    await asyncio.sleep(1)
                except Exception:
                    pass

                screenshot_bytes = await page.screenshot(full_page=False, type="png")
                await browser.close()
        except Exception as e:
            logger.error(f"Playwright screenshot failed for {url}: {e}")
            return {"valid": None, "notes": f"Screenshot failed: {e}"}

        # Send screenshot to Gemini Vision
        validation = await self.llm.validate_job_page_image(screenshot_bytes, country=country)

        # If the LLM returned an error dict (API failure, safety filter, etc.) treat as
        # inconclusive rather than marking the source invalid.
        if validation.get("error") or validation.get("api_error"):
            logger.warning(f"Gemini Vision API error for {url}: {validation}")
            return {
                "valid": None,
                "country_ok": False,
                "job_count": None,
                "confidence": "low",
                "notes": f"Vision API error: {validation.get('error') or validation.get('api_error')}",
                "screenshot": screenshot_bytes,
            }

        shows_jobs = validation.get("shows_job_listings")
        country_ok = validation.get("country_specific", False)
        notes = validation.get("notes", "")
        confidence = validation.get("confidence", "low")
        job_count = validation.get("job_count_estimate")

        # A page that is structurally a careers/jobs page for the correct country is valid
        # even if 0 current openings are visible (company may have no vacancies right now).
        if shows_jobs is None:
            # Vision returned no usable answer — inconclusive
            valid = None
        elif shows_jobs:
            valid = True
        elif country_ok and job_count == 0:
            # Careers page for the right country, just no current openings
            valid = True
            notes = f"[0 current openings but valid careers page] {notes}"
        else:
            valid = False

        logger.info(
            f"Visual validation [{confidence}] for {url}: "
            f"shows_jobs={shows_jobs}, country_ok={country_ok}, ~{job_count} jobs → valid={valid} — {notes}"
        )

        return {
            "valid": valid,
            "country_ok": bool(country_ok),
            "job_count": job_count,
            "confidence": confidence,
            "notes": notes,
            "screenshot": screenshot_bytes,
        }

    async def _scrape_for_country_url(self, url: str, country: str) -> str | None:
        """
        GET the page and look for href links that contain country-specific patterns
        AND point to a careers/jobs listing page (not a T&C, news, or individual job posting).
        Works well for server-rendered (non-JS-heavy) sites.
        """
        import asyncio
        import re as _re
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse, urljoin

        country_lower = country.lower()
        # Two-letter ISO code for the country (e.g. "ch" for Switzerland)
        cc = country[:2].lower()

        # Common patterns indicating a country-filtered jobs page
        patterns = [
            country_lower,              # "switzerland"
            f"/{cc}/",                  # "/ch/"
            f".{cc}/",                  # ".ch/"
            f"/{cc}-",                  # "/ch-"
            f"en-{cc}",                 # "en-ch"
            f"facetcountry={cc}",       # Workday/Taleo filters (case-insensitive)
            f"country={country}",       # "country=Switzerland"
            f"location={country}",      # "location=Switzerland"
            f"geoid=",                  # LinkedIn geoId (always country-specific)
            "/jobs/search",             # LinkedIn jobs search
        ]

        # Path must contain a career/job keyword to be considered a listing page
        CAREER_PATH_KW = (
            "/jobs", "/careers", "/career", "/vacancies", "/vacancy",
            "/offres", "/emploi", "/stellen", "/stelle", "/arbeit",
            "/work-with-us", "/join-us", "/open-positions", "/openings",
            "/recruitment", "/job-search", "/search",
            "myworkdayjobs.com", "greenhouse.io", "lever.co",
            "successfactors", "icims.com", "taleo.net",
            "smartrecruiters.com", "recruitee.com",
        )

        # Reject links that look like individual job postings:
        # e.g. /jobs/senior-engineer-zurich-12345 or /jobs/view/67890
        # Heuristic: path segment count > 4 after the careers root, OR has a numeric job ID at the end
        JOB_POSTING_RE = _re.compile(
            r"/jobs?/[^/?#]{40,}|"           # very long slug (likely a job title slug)
            r"/jobs?/.*?/\d{4,}|"            # /jobs/.../12345
            r"/jobs?/view/|"                 # /jobs/view/<id>
            r"/requisition/|"
            r"/job-detail/|"
            r"/jobdetail",
            _re.IGNORECASE,
        )

        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; CareerBot/1.0; +https://careerrev.io)"}
            resp = await asyncio.to_thread(
                requests.get, url, headers=headers, timeout=8, allow_redirects=True
            )
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # ATS platforms companies redirect to — always trust these cross-domain links
            ats_domains = {
                "myworkdayjobs.com", "greenhouse.io", "lever.co",
                "successfactors.eu", "successfactors.com", "icims.com",
                "taleo.net", "smartrecruiters.com", "recruitee.com",
            }
            base_netloc = urlparse(resp.url).netloc

            for tag in soup.find_all("a", href=True):
                href = tag["href"].strip()
                href_lower = href.lower()

                # Must contain a country pattern
                if not any(p in href_lower for p in patterns):
                    continue

                absolute = urljoin(resp.url, href)
                absolute_lower = absolute.lower()
                link_netloc = urlparse(absolute).netloc

                # Must point to a careers/jobs section
                if not any(kw in absolute_lower for kw in CAREER_PATH_KW):
                    continue

                # Must not be an individual job posting
                if JOB_POSTING_RE.search(absolute):
                    continue

                # Accept: same domain OR known ATS redirect
                is_same_domain = link_netloc == base_netloc
                is_ats = any(ats in link_netloc for ats in ats_domains)
                if is_same_domain or is_ats:
                    return absolute

            return None
        except Exception as e:
            logger.debug(f"Scrape failed for {url}: {e}")
            return None

    async def _llm_suggest_country_url(self, company_url: str, country: str) -> str | None:
        """Ask the LLM to suggest the country-specific jobs listing URL."""
        cc = country[:2].upper()
        prompt = f"""
You are a URL expert specialising in corporate careers pages. Given a company careers URL, return the EXACT URL that shows the job LISTINGS page filtered to {country}.

Company careers URL: {company_url}

Rules — follow ALL of them:
1. Return the URL of the LISTING page (shows multiple jobs), NOT a general careers landing page and NOT a single job posting.
2. Use ONLY URL patterns you are certain exist for this specific company. Common patterns:
   - Path-based country segment: /{country.lower()}/, /en-{cc.lower()}/, /ch/, /de/ etc.
   - Workday ATS: ?facetCountry={cc} — BUT only if you are 100% certain this company uses Workday. NEVER guess a Workday country GUID (the long hex string). If unsure, omit the facetCountry param.
   - SAP SuccessFactors: ?selected_fields=POSTING_DATE%2CCOUNTRY&COUNTRY={cc}
   - Greenhouse / Lever / Recruitee: these do NOT support country filter params — return the base jobs listing URL only.
   - SmartRecruiters: does NOT support ?location= or ?country= params — return the base jobs URL only.
   - Jobvite: does NOT support ?location= params — return the base jobs URL only.
3. If you do not know the country-specific URL with confidence, return the base jobs/careers listing URL without any invented parameters.
4. Return ONLY a valid JSON object — no markdown, no explanation.

{{"vetted_url": "https://..."}}
"""
        try:
            response = await self.llm._get_gemini_response(prompt)
            if isinstance(response, dict):
                url = response.get("vetted_url", "")
                if url and url.startswith("http"):
                    return url.strip()
        except Exception as e:
            logger.error(f"LLM URL suggestion failed for {company_url}: {e}")
        return None

    async def _http_verify_url(self, url: str) -> bool:
        """Return True if the URL resolves with a 2xx/3xx status."""
        import asyncio
        import requests
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; CareerBot/1.0)"}
            resp = await asyncio.to_thread(
                requests.head, url, headers=headers, timeout=6, allow_redirects=True
            )
            return resp.status_code < 400
        except Exception:
            return False

    def _get_default_sources(self, location: str, industry: str) -> List[Dict[str, Any]]:
        """Return curated seed sources for the given country, falling back to Switzerland."""
        try:
            from app.services.source_seed_data import get_seed_sources
            seeds = get_seed_sources(location)
            if seeds:
                logger.info(f"Using {len(seeds)} curated seed sources for {location}")
                return seeds
        except Exception as e:
            logger.error(f"Failed to load seed sources: {e}")

        # Absolute last-resort defaults
        return [
            {
                "name": "LinkedIn",
                "url": "https://www.linkedin.com/jobs/",
                "source_type": "global_with_local",
                "industry": "General",
                "sector": "General",
                "reasoning": "Global standard for professional networking and job search.",
                "quality_score": 90,
                "tags": [location, "General", "Global"]
            },
            {
                "name": "Indeed",
                "url": f"https://www.indeed.com/jobs?l={location}",
                "source_type": "global_with_local",
                "industry": "General",
                "sector": "General",
                "reasoning": "Leading global job board with local filtering.",
                "quality_score": 80,
                "tags": [location, "General", "Global"]
            }
        ]
