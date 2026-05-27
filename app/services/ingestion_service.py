"""
Ingestion Service — fetches actual job listings from all active sources.

Tier strategy (fastest/most reliable first):
  Tier 1  Portal JSON APIs        jobs.ch, Jobup.ch (known internal APIs)
  Tier 2  ATS Public APIs         Greenhouse (boards.greenhouse.io/v1/boards/{co}/jobs)
                                  Lever      (api.lever.co/v0/postings/{co}?mode=json)
                                  Workday    (search API via known pattern)
  Tier 3  Structured HTML         BeautifulSoup on static/SSR pages
  Tier 4  JS-rendered (Playwright) Only when Tiers 1-3 return nothing

All portals (standard_portal, global_with_local, government_portal, boutique_recruiter)
are queried via Tier 3/4, not just company pages.
"""

import logging
import requests
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import quote_plus, urljoin, urlparse, urlunparse, parse_qsl, urlencode
from bs4 import BeautifulSoup
from app.services.discovery_engine import SearchResult
from app.config import settings

logger = logging.getLogger(__name__)


# ── ATS detection patterns ────────────────────────────────────────────────────
ATS_PATTERNS = {
    "workday":      r"([\w-]+)\.wd\d+\.myworkdayjobs\.com",
    "greenhouse":   r"boards\.greenhouse\.io/([\w-]+)",
    "lever":        r"jobs\.lever\.co/([\w-]+)",
}


class IngestionService:
    """Fetch job listings from all active sources in the DB."""

    def __init__(self):
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        self._playwright_browser = None  # Shared browser instance across calls

    # ── Public API ─────────────────────────────────────────────────────────────

    async def ingest_from_source(
        self,
        source_name: str,
        source_url: str,
        source_type: str,
        location_filter: str = "",
        keyword: str = "",
        max_pages: int = 5,
    ) -> List[SearchResult]:
        """
        Route a single source to the best available ingestion strategy.
        Called for every active source in the DB during Refresh Jobs.
        """
        url_lower = source_url.lower()

        # Tier 1 — Portal JSON APIs (instant, structured)
        if "jobs.ch" in url_lower:
            return await self._ingest_jobs_ch(location_filter, keyword)
        if "jobup.ch" in url_lower or "jobcloud.ch" in url_lower:
            return await self._ingest_jobup(location_filter, keyword)

        # Tier 2 — ATS Public APIs (structured, no scraping needed)
        ats = self._detect_ats(source_url)
        if ats:
            return await self._ingest_ats(source_name, source_url, ats, location_filter)

        # Tier 3/4 — Generic HTML/JS scraping with pagination
        return await self._ingest_generic_page(source_name, source_url, max_pages)

    async def ingest_all_sources(
        self,
        sources: List[Dict],
        location_filter: str = "Switzerland",
        max_concurrent: int = 8,
    ) -> List[SearchResult]:
        """
        Ingest jobs from all provided sources concurrently.
        `sources` is a list of dicts: {name, url, source_type}
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        PER_SOURCE_TIMEOUT = 60  # seconds — prevents any one source hanging the whole pipeline

        async def safe_ingest(src):
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self.ingest_from_source(
                            src["name"], src["url"], src.get("source_type", ""),
                            location_filter=location_filter
                        ),
                        timeout=PER_SOURCE_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Ingestion timed out after {PER_SOURCE_TIMEOUT}s: {src['name']} ({src['url']})")
                    return []
                except Exception as e:
                    logger.error(f"Ingestion failed for {src['name']}: {e}")
                    return []

        results = await asyncio.gather(*[safe_ingest(s) for s in sources])
        # Flatten and tag each result with its source DB id
        flat = []
        for src, batch in zip(sources, results):
            if isinstance(batch, list):
                for r in batch:
                    if r.source_db_id is None and src.get("id"):
                        r.source_db_id = src["id"]
                flat.extend(batch)
        return flat

    # ── Tier 1: Portal JSON APIs ───────────────────────────────────────────────

    async def _ingest_jobs_ch(self, location: str = "", keyword: str = "") -> List[SearchResult]:
        """Jobs.ch internal search API — returns up to 100 jobs per call."""
        url = "https://job-search-api.jobs.ch/search?rows=100&publication-date=7d"
        if keyword:
            url += f"&term={quote_plus(keyword)}"
        if location and location.lower() not in ("switzerland", ""):
            loc = "Geneva" if "romandie" in location.lower() else location
            url += f"&location={quote_plus(loc)}"

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Referer": "https://www.jobs.ch/",
        }
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, headers=headers, timeout=15)
            )
            if resp.status_code != 200:
                return []
            results = []
            for doc in resp.json().get("documents", []):
                job_id = doc.get("id")
                if not job_id:
                    continue
                title = doc.get("title", "Unknown")
                company = doc.get("company", {}).get("name", "Unknown")
                place = doc.get("place", "Switzerland")
                results.append(SearchResult(
                    title=f"{title} @ {company}",
                    url=f"https://www.jobs.ch/en/vacancies/detail/{job_id}/",
                    snippet=f"{place} · {doc.get('publicationDate', '')}",
                    source="api_jobs.ch",
                    location=place,
                ))
            logger.info(f"jobs.ch API: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"jobs.ch API error: {e}")
            return []

    async def _ingest_jobup(self, location: str = "", keyword: str = "") -> List[SearchResult]:
        """Jobup.ch / JobCloud API."""
        url = "https://api.jobup.ch/v1/jobs?limit=100"
        if keyword:
            url += f"&query={quote_plus(keyword)}"
        if location and location.lower() not in ("switzerland", ""):
            url += f"&location={quote_plus(location)}"
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, headers=headers, timeout=15)
            )
            if resp.status_code != 200:
                return []
            results = []
            for job in resp.json().get("jobs", []):
                job_id = job.get("id")
                title = job.get("title", "Unknown")
                company = job.get("company", {}).get("name", "Unknown")
                place = job.get("location", {}).get("city", "Switzerland")
                if job_id:
                    results.append(SearchResult(
                        title=f"{title} @ {company}",
                        url=f"https://www.jobup.ch/en/jobs/detail/{job_id}/",
                        snippet=place,
                        source="api_jobup.ch",
                        location=place,
                    ))
            logger.info(f"Jobup.ch API: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Jobup API error: {e}")
            return []

    # ── Tier 2: ATS APIs ───────────────────────────────────────────────────────

    def _detect_ats(self, url: str) -> Optional[Dict]:
        """Return ATS type and company slug if URL matches a known ATS pattern."""
        for ats_name, pattern in ATS_PATTERNS.items():
            m = re.search(pattern, url, re.IGNORECASE)
            if m:
                return {"type": ats_name, "slug": m.group(1)}
        return None

    async def _ingest_ats(
        self, source_name: str, url: str, ats: Dict, location_filter: str
    ) -> List[SearchResult]:
        ats_type = ats["type"]
        slug = ats["slug"]
        if ats_type == "greenhouse":
            return await self._ingest_greenhouse(source_name, slug, location_filter)
        if ats_type == "lever":
            return await self._ingest_lever(source_name, slug, location_filter)
        if ats_type == "workday":
            # Workday has no public API — fall through to generic scraping
            return await self._ingest_generic_page(source_name, url, max_pages=3)
        return []

    async def _ingest_greenhouse(
        self, company_name: str, slug: str, location_filter: str
    ) -> List[SearchResult]:
        """Greenhouse public API — no auth required."""
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(api_url, timeout=15)
            )
            if resp.status_code != 200:
                return []
            results = []
            loc_lower = location_filter.lower()
            for job in resp.json().get("jobs", []):
                job_loc = (job.get("location", {}).get("name", "") or "").lower()
                # Filter by location if specified
                if loc_lower and loc_lower not in ("", "worldwide") and loc_lower not in job_loc and "remote" not in job_loc:
                    continue
                results.append(SearchResult(
                    title=f"{job['title']} @ {company_name}",
                    url=job.get("absolute_url", ""),
                    snippet=job.get("location", {}).get("name", ""),
                    source=f"ats_greenhouse_{slug}",
                    location=job.get("location", {}).get("name", ""),
                ))
            logger.info(f"Greenhouse {slug}: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Greenhouse API error for {slug}: {e}")
            return []

    async def _ingest_lever(
        self, company_name: str, slug: str, location_filter: str
    ) -> List[SearchResult]:
        """Lever public API — no auth required."""
        api_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(api_url, timeout=15)
            )
            if resp.status_code != 200:
                return []
            results = []
            loc_lower = location_filter.lower()
            for job in resp.json():
                job_loc = (job.get("categories", {}).get("location", "") or "").lower()
                if loc_lower and loc_lower not in ("", "worldwide") and loc_lower not in job_loc and "remote" not in job_loc:
                    continue
                results.append(SearchResult(
                    title=f"{job['text']} @ {company_name}",
                    url=job.get("hostedUrl", ""),
                    snippet=job.get("categories", {}).get("location", ""),
                    source=f"ats_lever_{slug}",
                    location=job.get("categories", {}).get("location", ""),
                ))
            logger.info(f"Lever {slug}: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Lever API error for {slug}: {e}")
            return []

    # ── Tier 3/4: Generic Scraping ─────────────────────────────────────────────

    async def _ingest_generic_page(
        self, source_name: str, url: str, max_pages: int = 5
    ) -> List[SearchResult]:
        """
        Paginated scraper. Tries requests first; falls back to Playwright if
        the page has no job links (probable JS-rendered SPA).
        """
        all_results: List[SearchResult] = []
        seen_links: set = set()
        pages_visited: set = set()
        pages_to_visit = [url]

        while pages_to_visit and len(pages_visited) < max_pages:
            current_url = pages_to_visit.pop(0)
            if current_url in pages_visited:
                continue
            pages_visited.add(current_url)

            html = await self._fetch_html_requests(current_url)
            page_results, next_pages = self._parse_job_links(
                html, current_url, source_name, seen_links
            )

            # If static HTML returns nothing, try Playwright once for this page
            if not page_results and not next_pages:
                html = await self._fetch_html_playwright(current_url)
                page_results, next_pages = self._parse_job_links(
                    html, current_url, source_name, seen_links
                )

            all_results.extend(page_results)
            for np in next_pages:
                if np not in pages_visited and np not in pages_to_visit:
                    pages_to_visit.append(np)

            await asyncio.sleep(0.4)  # Polite delay

        logger.info(f"{source_name}: {len(all_results)} jobs from {len(pages_visited)} page(s)")
        return all_results

    async def _fetch_html_requests(self, url: str) -> str:
        headers = {"User-Agent": self.user_agent}
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None, lambda: requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            )
            return resp.text if resp.status_code == 200 else ""
        except Exception as e:
            logger.debug(f"requests failed for {url}: {e}")
            return ""

    async def _fetch_html_playwright(self, url: str) -> str:
        """Render a single URL with Playwright. Reuses browser if already open."""
        # Firecrawl first (if configured) — handles anti-bot better
        if settings.firecrawl_api_key:
            try:
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(None, lambda: requests.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    headers={
                        "Authorization": f"Bearer {settings.firecrawl_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"url": url, "formats": ["html"]},
                    timeout=30,
                ))
                if resp.status_code == 200:
                    html = resp.json().get("data", {}).get("html", "")
                    if html:
                        return html
            except Exception as e:
                logger.debug(f"Firecrawl error for {url}: {e}")

        # Playwright fallback — hard 30s cap via wait_for so it can't stall the pipeline
        async def _playwright_fetch():
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    user_agent=self.user_agent, viewport={"width": 1280, "height": 900}
                )
                page = await ctx.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    pass
                await asyncio.sleep(2)
                html = await page.content()
                await browser.close()
                return html

        try:
            return await asyncio.wait_for(_playwright_fetch(), timeout=30)
        except asyncio.TimeoutError:
            logger.warning(f"Playwright timed out for {url}")
            return ""
        except Exception as e:
            logger.debug(f"Playwright error for {url}: {e}")
            return ""

    def _parse_job_links(
        self,
        html: str,
        page_url: str,
        source_name: str,
        seen_links: set,
    ) -> Tuple[List[SearchResult], List[str]]:
        """
        Extract individual job links and pagination links from a rendered HTML page.
        Allows cross-domain links to handle ATS redirects (Workday, Greenhouse, etc.).
        """
        if not html:
            return [], []

        def normalize(u: str) -> str:
            p = urlparse(u)
            q = [(k, v) for k, v in parse_qsl(p.query)
                 if k.lower() not in ("lang", "utm_source", "utm_medium", "utm_campaign", "ref")]
            return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), ""))

        soup = BeautifulSoup(html, "html.parser")
        results, next_pages = [], []

        # Known ATS external domains — always allow links to these even if cross-domain
        ats_domains = {
            "myworkdayjobs.com", "greenhouse.io", "lever.co",
            "successfactors.eu", "successfactors.com", "icims.com",
            "taleo.net", "jobvite.com", "smartrecruiters.com",
            "recruitee.com", "ashbyhq.com", "bamboohr.com",
        }

        job_kw = [
            "job", "vacancy", "vacancies", "position", "opening", "role",
            "stellen", "offene", "detail", "requisition", "/careers/",
            "/en/job", "/en/vacancies", "apply", "workday", "greenhouse",
            "lever.co", "successfactors", "/careersection/", "jobdetail",
        ]
        bad_kw = [
            "about", "culture", "benefits", "leadership", "story", "teams",
            "working-at", "diversity", "contact", "login", "register",
            "newsletter", "subscribe", "cookies", "terms", "privacy",
            "settings", "find-job", "explore", "work-at",
        ]
        page_kw = ["next", "weiter", "suivant", "page=", "/page/", "?p=", "&page=", "offset="]

        generic_labels = {
            "apply now", "view job", "read more", "learn more", "apply",
            "mehr erfahren", "details", "click here", "show more", "zur stelle",
            "job details", "view details",
        }

        base_netloc = urlparse(page_url).netloc

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = " ".join(a.get_text().split())

            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue

            absolute = normalize(urljoin(page_url, href))
            parsed = urlparse(absolute)
            link_domain = parsed.netloc

            # Allow: same domain OR known ATS domain
            is_same_domain = link_domain == base_netloc
            is_ats = any(ats in link_domain for ats in ats_domains)
            if not is_same_domain and not is_ats:
                continue

            hl = absolute.lower()
            tl = text.lower()

            # Pagination detection
            if any(pk in hl or pk in tl for pk in page_kw):
                next_pages.append(absolute)
                continue

            is_job = any(k in hl or k in tl for k in job_kw)
            is_bad = any(b in hl or b in tl for b in bad_kw)
            if not is_job or is_bad:
                continue

            # Clean title
            title = text.strip()
            if not title or tl in generic_labels or len(title) < 5:
                # Try URL slug as fallback title
                parts = [p for p in parsed.path.split("/") if p]
                if parts:
                    slug = parts[-1].replace("-", " ").replace("_", " ")
                    slug = re.sub(r"\.(html?|php|aspx?)$", "", slug, flags=re.I)
                    if len(slug) > 10:
                        title = slug.title()
                    else:
                        continue
            if len(title) > 8 and absolute not in seen_links:
                seen_links.add(absolute)
                results.append(SearchResult(
                    title=f"{title[:120]} @ {source_name}",
                    url=absolute,
                    snippet=f"Discovered via {source_name}",
                    source=f"direct_{source_name}",
                    source_db_id=None,
                ))

            if len(results) >= 60:
                break

        return results, next_pages
