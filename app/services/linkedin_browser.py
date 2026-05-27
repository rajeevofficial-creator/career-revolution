"""
LinkedIn Browser Service — authenticated Playwright session.

Design principles:
- One session per user (cookies stored encrypted in DB).
- Human-like pacing: random delays, natural scroll before click.
- Login only when cookies are missing or expired; reuse otherwise.
- Never run multiple concurrent requests within the same session.
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta

from playwright_stealth import Stealth

_stealth = Stealth()
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.database import LinkedInSession, LinkedInJob
from app.utils.security import encrypt_value, decrypt_value

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stealth browser configuration
# ---------------------------------------------------------------------------
_STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-gpu",
    "--window-size=1280,900",
    "--lang=en-US,en",
    # Prevent navigator.plugins from being empty (common bot signal)
    "--use-fake-ui-for-media-stream",
    # Match a real Chrome install more closely
    "--disable-features=IsolateOrigins,site-per-process",
]

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# JS injected into every page to mask automation fingerprints
_STEALTH_INIT_SCRIPT = """
// Hide webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// Fake plugin list (headless Chrome has 0 plugins — a strong bot signal)
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        {name:'Chrome PDF Plugin', filename:'internal-pdf-viewer', description:'Portable Document Format'},
        {name:'Chrome PDF Viewer', filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai', description:''},
        {name:'Native Client', filename:'internal-nacl-plugin', description:''},
    ]
});

// Non-zero language list
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'de']});

// Chrome object present in real browsers
window.chrome = window.chrome || {runtime: {}};

// Prevent iframe contentWindow detection
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (params) =>
    (params.name === 'notifications')
        ? Promise.resolve({state: Notification.permission})
        : origQuery(params);
"""

# Cookies are considered stale after 25 days (LinkedIn sessions ~30 days)
SESSION_TTL_DAYS = 25

# Minimum gap between fetch calls — don't hammer LinkedIn
_MIN_FETCH_INTERVAL_MINUTES = 30


async def _human_delay(lo: float = 1.2, hi: float = 3.0):
    await asyncio.sleep(random.uniform(lo, hi))


async def _human_scroll(page, rounds: int = 3, px: int = 700):
    """Scroll with slight randomness, like a person reading down the page."""
    for _ in range(rounds):
        delta = px + random.randint(-150, 150)
        await page.mouse.wheel(0, delta)
        await _human_delay(0.8, 1.8)


async def _human_click_more(page):
    """Try to find and click 'Show more' button to expand job description."""
    show_more_selectors = [
        "button.jobs-description__footer-button",
        "button.show-more-less-html__button",
        ".jobs-description__content button.artdeco-button--muted",
        "button[aria-label='Show more description']",
        "button[data-testid='expandable-text-button']"
    ]
    for selector in show_more_selectors:
        try:
            btn = await page.query_selector(selector)
            if btn and await btn.is_visible():
                # Move mouse to button first
                box = await btn.bounding_box()
                if box:
                    await page.mouse.move(
                        box["x"] + box["width"] / 2 + random.uniform(-5, 5),
                        box["y"] + box["height"] / 2 + random.uniform(-5, 5)
                    )
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                
                await btn.click()
                logger.info(f"[LinkedIn] Clicked 'Show more' button ({selector})")
                await asyncio.sleep(random.uniform(1.0, 2.0))
                return True
        except Exception:
            continue
    return False


async def _slow_type(page, selector: str, text: str):
    """Type into a field character-by-character with human-like timing."""
    await page.click(selector)
    for ch in text:
        await page.keyboard.type(ch)
        await asyncio.sleep(random.uniform(0.05, 0.18))


class LinkedInBrowserService:
    """
    Manages a Playwright browser session for one LinkedIn user account.
    All public methods are async; call them one at a time (no parallel use).
    """

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def session_status(self, db: Session, user_id: int) -> Dict:
        """Return connection status for the frontend."""
        row = db.query(LinkedInSession).filter(LinkedInSession.user_id == user_id).first()
        has_credentials = row is not None and row.linkedin_email_enc is not None and row.linkedin_pw_enc is not None
        if not row or not row.is_valid:
            return {
                "connected": False,
                "stale": False,
                "has_credentials": has_credentials,
                "profile_name": None,
                "last_fetch": None
            }
        stale = (
            not row.last_login_at
            or datetime.utcnow() - row.last_login_at > timedelta(days=SESSION_TTL_DAYS)
        )
        return {
            "connected": not stale,
            "stale": stale,
            "has_credentials": has_credentials,
            "profile_name": row.profile_name,
            "profile_url": row.profile_url,
            "last_login": row.last_login_at.isoformat() if row.last_login_at else None,
            "last_fetch": row.last_fetch_at.isoformat() if row.last_fetch_at else None,
        }

    def save_credentials(self, db: Session, user_id: int, email: str, password: str):
        """Encrypt and persist LinkedIn credentials (does NOT log in yet)."""
        row = db.query(LinkedInSession).filter(LinkedInSession.user_id == user_id).first()
        if not row:
            row = LinkedInSession(user_id=user_id)
            db.add(row)
        row.linkedin_email_enc = encrypt_value(email)
        row.linkedin_pw_enc = encrypt_value(password)
        row.is_valid = False
        db.commit()

    def disconnect(self, db: Session, user_id: int):
        """Clear session — user will need to reconnect."""
        row = db.query(LinkedInSession).filter(LinkedInSession.user_id == user_id).first()
        if row:
            row.cookies_enc = None
            row.is_valid = False
            row.profile_name = None
            db.commit()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, db: Session, user_id: int) -> Tuple[bool, str]:
        """
        Open LinkedIn, log in with stored credentials, save cookies.
        Returns (success, message).
        """
        row = db.query(LinkedInSession).filter(LinkedInSession.user_id == user_id).first()
        if not row or not row.linkedin_email_enc:
            return False, "No credentials stored. Please connect first."

        email = decrypt_value(row.linkedin_email_enc)
        password = decrypt_value(row.linkedin_pw_enc)
        if not email or not password:
            return False, "Could not decrypt credentials."

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True, args=_STEALTH_ARGS
                )
                ctx = await browser.new_context(
                    user_agent=_USER_AGENT,
                    viewport={"width": 1280, "height": 900},
                    locale="en-US",
                    timezone_id="Europe/Zurich",
                )
                await ctx.add_init_script(_STEALTH_INIT_SCRIPT)
                page = await ctx.new_page()
                await _stealth.apply_stealth_async(page)

                try:
                    logger.info(f"[LinkedIn] Navigating to login page for user {user_id}")
                    await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
                    await _human_delay(2.0, 3.0)

                    # Target visible inputs by type and visibility (resilient to React 18 dynamic IDs like :r3: and translations)
                    email_input = page.locator("input[type='email']:visible")
                    pw_input = page.locator("input[type='password']:visible")

                    await email_input.wait_for(state="visible", timeout=10000)
                    await email_input.fill(email)
                    await _human_delay(0.5, 1.0)
                    await pw_input.fill(password)
                    await _human_delay(0.8, 1.5)

                    # Debug: Save screenshot before clicking submit
                    try:
                        import os
                        os.makedirs("scratch", exist_ok=True)
                        await page.screenshot(path="scratch/app_before_submit.png")
                        logger.info(f"[LinkedIn] Saved app_before_submit.png. Page title: {await page.title()}, URL: {page.url}")
                    except Exception as sse:
                        logger.error(f"[LinkedIn] Failed to save pre-submit screenshot: {sse}")

                    # "Sign in" button — use type and visibility (resilient to translation)
                    sign_in_btn = page.locator("button[type='submit']:visible")
                    await sign_in_btn.click()
                    await _human_delay(4.0, 6.0)

                    # Check for 2FA / security challenge
                    current_url = page.url
                    if "checkpoint" in current_url or "challenge" in current_url:
                        await browser.close()
                        return False, "LinkedIn requires verification (2FA/security check). Please complete it manually in your browser once, then try reconnecting."

                    if "feed" not in current_url and "mynetwork" not in current_url and "jobs" not in current_url:
                        # Still on login — try to read error text from page
                        error_el = (
                            await page.query_selector("[role='alert']") or
                            await page.query_selector(".alert") or
                            await page.query_selector("form .error")
                        )
                        error_msg = (await error_el.inner_text()).strip() if error_el else f"Unexpected page: {current_url}"
                        await browser.close()
                        return False, f"Login failed: {error_msg}"

                    # Grab profile name from nav
                    profile_name = None
                    profile_url = None
                    try:
                        await page.goto("https://www.linkedin.com/in/me", wait_until="domcontentloaded", timeout=15000)
                        await _human_delay(1.5, 2.5)
                        profile_url = page.url
                        title = await page.title()
                        # Title is usually "Name | LinkedIn"
                        profile_name = title.split("|")[0].strip() if "|" in title else None
                    except Exception:
                        pass

                    # Save cookies
                    cookies = await ctx.cookies()
                    await browser.close()

                    row.cookies_enc = encrypt_value(json.dumps(cookies))
                    row.is_valid = True
                    row.last_login_at = datetime.utcnow()
                    row.profile_name = profile_name
                    row.profile_url = profile_url
                    db.commit()

                    logger.info(f"[LinkedIn] Login successful for user {user_id} ({profile_name})")
                    return True, f"Connected as {profile_name or email}"
                except Exception as inner_e:
                    import os
                    os.makedirs("scratch", exist_ok=True)
                    try:
                        await page.screenshot(path="scratch/app_login_error.png")
                        logger.info("Saved error screenshot to scratch/app_login_error.png")
                    except Exception as ss_e:
                        logger.error(f"Failed to capture screenshot inside try: {ss_e}")
                    raise inner_e

        except Exception as e:
            logger.error(f"[LinkedIn] Login error for user {user_id}: {e}")
            try:
                if 'page' in locals() and page:
                    import os
                    os.makedirs("scratch", exist_ok=True)
                    await page.screenshot(path="scratch/app_login_error.png")
                    logger.info("Saved error screenshot to scratch/app_login_error.png")
            except Exception as se:
                logger.error(f"Failed to save error screenshot: {se}")
            return False, f"Browser error: {e}"

    # ------------------------------------------------------------------
    # Job fetching
    # ------------------------------------------------------------------

    async def fetch_jobs(
        self,
        db: Session,
        user_id: int,
        keyword: str = "",
        max_jobs: int = 50,
        fetch_source: str = "jobs_for_you",
    ) -> Tuple[bool, str, int]:
        """
        Fetch LinkedIn jobs for the user.
        fetch_source: "jobs_for_you" | "search"
        Returns (success, message, new_jobs_count).
        """
        row = db.query(LinkedInSession).filter(LinkedInSession.user_id == user_id).first()
        if not row or not row.is_valid or not row.cookies_enc:
            return False, "Not connected. Please connect to LinkedIn first.", 0

        # Throttle: don't hit LinkedIn more often than once per 30 min
        if row.last_fetch_at:
            mins_since = (datetime.utcnow() - row.last_fetch_at).total_seconds() / 60
            if mins_since < _MIN_FETCH_INTERVAL_MINUTES:
                wait = int(_MIN_FETCH_INTERVAL_MINUTES - mins_since)
                return False, f"Please wait {wait} more minute(s) before fetching again.", 0

        # Re-login if session cookies are stale
        if row.last_login_at and datetime.utcnow() - row.last_login_at > timedelta(days=SESSION_TTL_DAYS):
            ok, msg = await self.login(db, user_id)
            if not ok:
                return False, f"Session expired and re-login failed: {msg}", 0
            row = db.query(LinkedInSession).filter(LinkedInSession.user_id == user_id).first()

        try:
            cookies = json.loads(decrypt_value(row.cookies_enc))
        except Exception:
            return False, "Could not load session cookies.", 0

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=_STEALTH_ARGS)
                ctx = await browser.new_context(
                    user_agent=_USER_AGENT,
                    viewport={"width": 1280, "height": 900},
                    locale="en-US",
                    timezone_id="Europe/Zurich",
                )
                await ctx.add_init_script(_STEALTH_INIT_SCRIPT)
                await ctx.add_cookies(cookies)
                page = await ctx.new_page()
                await _stealth.apply_stealth_async(page)

                jobs_data = []

                if fetch_source == "jobs_for_you":
                    jobs_data = await self._scrape_jobs_for_you(page, max_jobs)
                else:
                    jobs_data = await self._scrape_job_search(page, keyword, max_jobs)

                await browser.close()

            # Persist results
            new_count = self._save_jobs(db, user_id, jobs_data, fetch_source)
            row.last_fetch_at = datetime.utcnow()
            db.commit()

            logger.info(f"[LinkedIn] Fetched {len(jobs_data)} raw, saved {new_count} new jobs for user {user_id}")
            return True, f"Fetched {len(jobs_data)} jobs, {new_count} new.", new_count

        except Exception as e:
            logger.error(f"[LinkedIn] Fetch error for user {user_id}: {e}")
            return False, f"Fetch error: {e}", 0

    # ------------------------------------------------------------------
    # Scrapers
    # ------------------------------------------------------------------

    async def _scrape_jobs_for_you(self, page, max_jobs: int) -> List[Dict]:
        """Scrape LinkedIn's personalised 'Jobs for You' collection."""
        logger.info("[LinkedIn] Fetching 'Jobs for You' from collections/recommended")
        await page.goto(
            "https://www.linkedin.com/jobs/collections/recommended/",
            wait_until="domcontentloaded",
            timeout=25000,
        )
        # Wait for the first job card to appear (React hydration)
        try:
            await page.wait_for_selector("[data-occludable-job-id]", timeout=15000)
        except Exception:
            logger.warning("[LinkedIn] Timed out waiting for job cards on recommended page")
        await _human_delay(2.0, 3.0)
        return await self._extract_job_cards(page, max_jobs)

    async def _scrape_job_search(self, page, keyword: str, max_jobs: int) -> List[Dict]:
        """Scrape LinkedIn job search results for a keyword, filtered to Switzerland."""
        from urllib.parse import quote_plus
        kw = keyword or "IT Director"
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={quote_plus(kw)}"
            f"&geoId=106693272"   # Switzerland geoId
            f"&f_TPR=r604800"     # Posted in last 7 days
            f"&sortBy=R"          # Relevance
        )
        logger.info(f"[LinkedIn] Searching jobs: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        try:
            await page.wait_for_selector("[data-occludable-job-id]", timeout=15000)
        except Exception:
            logger.warning("[LinkedIn] Timed out waiting for job cards on search page")
        await _human_delay(2.0, 3.0)
        return await self._extract_job_cards(page, max_jobs)

    async def _extract_job_cards(self, page, max_jobs: int) -> List[Dict]:
        """
        Scroll the job list panel and extract all card data via a single JS call per pass.
        Uses [data-occludable-job-id] — confirmed selector on LinkedIn's current React UI.
        """
        import re
        seen_ids: set = set()
        jobs: List[Dict] = []

        for scroll_round in range(8):
            # Human-like mouse wheel scroll — not a JS inject
            await _human_scroll(page, rounds=2, px=700)
            await _human_delay(1.5, 2.5)

            # Extract all card data in one JS round-trip (fast + reliable)
            raw_cards = await page.evaluate(
                """() => {
                    return Array.from(document.querySelectorAll('[data-occludable-job-id]'))
                        .map(card => {
                            const jobId = card.getAttribute('data-occludable-job-id') || '';
                            const titleEl = card.querySelector(
                                '.job-card-list__title, .job-card-container__link');
                            const companyEl = card.querySelector(
                                '.artdeco-entity-lockup__subtitle, .job-card-container__company-name');
                            const locationEl = card.querySelector(
                                '.job-card-container__metadata-item');
                            const linkEl = card.querySelector("a[href*='/jobs/view/']");
                            const insightEl = card.querySelector(
                                '[class*="insight"], [class*="connections"]');
                            const easyApplyEl = card.querySelector(
                                '[aria-label*="Easy Apply"], [class*="easy-apply"], '  +
                                '.job-card-container__apply-method');
                            const timeEl = card.querySelector('time');

                            return {
                                jobId,
                                title: titleEl
                                    ? titleEl.innerText.trim().split('\\n')[0].trim()
                                    : '',
                                company: companyEl
                                    ? companyEl.innerText.trim().split('\\n')[0].trim()
                                    : '',
                                location: locationEl
                                    ? locationEl.innerText.trim().split('\\n')[0].trim()
                                    : '',
                                jobUrl: linkEl ? linkEl.href : '',
                                easyApply: !!easyApplyEl,
                                network: insightEl
                                    ? insightEl.innerText.trim().substring(0, 120)
                                    : '',
                                posted: timeEl ? timeEl.innerText.trim() : '',
                            };
                        });
                }"""
            )

            for rc in raw_cards:
                if len(jobs) >= max_jobs:
                    break
                job_id = rc.get("jobId", "").strip()
                # Also try extracting ID from URL if attribute missing
                if not job_id and rc.get("jobUrl"):
                    m = re.search(r"/jobs/view/(\d+)", rc["jobUrl"])
                    job_id = m.group(1) if m else ""
                if not job_id or not rc.get("title") or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                jobs.append({
                    "linkedin_job_id": job_id,
                    "title": rc["title"][:500],
                    "company": (rc.get("company") or "Unknown")[:255],
                    "location": rc.get("location", "")[:255],
                    "job_url": f"https://www.linkedin.com/jobs/view/{job_id}/",
                    "easy_apply": rc.get("easyApply", False),
                    "posted_at_text": rc.get("posted", "")[:100],
                    "network_overlap": rc.get("network", "")[:100],
                })

            if len(jobs) >= max_jobs:
                break

        logger.info(f"[LinkedIn] Extracted {len(jobs)} job cards")
        return jobs

    # ------------------------------------------------------------------
    # Persist
    # ------------------------------------------------------------------

    def _save_jobs(self, db: Session, user_id: int, jobs: List[Dict], fetch_source: str) -> int:
        """Upsert LinkedIn jobs into linkedin_jobs table. Returns new row count."""
        new_count = 0
        for j in jobs:
            if not j.get("linkedin_job_id") or not j.get("title"):
                continue
            existing = db.query(LinkedInJob).filter(
                LinkedInJob.user_id == user_id,
                LinkedInJob.linkedin_job_id == j["linkedin_job_id"],
            ).first()
            if existing:
                existing.is_live = True
                existing.easy_apply = j.get("easy_apply", False)
                existing.network_overlap = j.get("network_overlap", "")
            else:
                db.add(LinkedInJob(
                    user_id=user_id,
                    linkedin_job_id=j["linkedin_job_id"],
                    title=j["title"],
                    company=j["company"],
                    location=j.get("location", ""),
                    job_url=j["job_url"],
                    easy_apply=j.get("easy_apply", False),
                    network_overlap=j.get("network_overlap", ""),
                    posted_at_text=j.get("posted_at_text", ""),
                    fetch_source=fetch_source,
                ))
                new_count += 1
        db.commit()
        return new_count

    def get_jobs(self, db: Session, user_id: int, page: int = 1, size: int = 20) -> Dict:
        """Return paginated LinkedIn jobs for a user."""
        q = (
            db.query(LinkedInJob)
            .filter(LinkedInJob.user_id == user_id, LinkedInJob.is_live == True)
            .order_by(LinkedInJob.first_seen_at.desc())
        )
        total = q.count()
        rows = q.offset((page - 1) * size).limit(size).all()
        return {
            "jobs": [
                {
                    "id": r.id,
                    "title": r.title,
                    "company": r.company,
                    "location": r.location,
                    "job_url": r.job_url,
                    "easy_apply": r.easy_apply,
                    "network_overlap": r.network_overlap,
                    "posted_at_text": r.posted_at_text,
                    "relevance_score": r.relevance_score,
                    "fetch_source": r.fetch_source,
                    "first_seen_at": r.first_seen_at.isoformat(),
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "pages": max(1, (total + size - 1) // size),
        }

    async def fetch_job_description(self, db: Session, user_id: int, job_url: str) -> Optional[str]:
        """
        Fetch the full job description for a specific LinkedIn job URL using the user's session.
        """
        row = db.query(LinkedInSession).filter(LinkedInSession.user_id == user_id).first()
        if not row or not row.is_valid or not row.cookies_enc:
            logger.warning(f"[LinkedIn] No valid session for user {user_id} to fetch JD")
            return None

        try:
            cookies = json.loads(decrypt_value(row.cookies_enc))
        except Exception:
            return None

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=_STEALTH_ARGS)
                ctx = await browser.new_context(
                    user_agent=_USER_AGENT,
                    viewport={"width": 1280, "height": 900},
                    locale="en-US",
                    timezone_id="Europe/Zurich",
                )
                await ctx.add_init_script(_STEALTH_INIT_SCRIPT)
                await ctx.add_cookies(cookies)
                page = await ctx.new_page()
                await _stealth.apply_stealth_async(page)

                logger.info(f"[LinkedIn] Fetching JD for user {user_id} from {job_url}")
                try:
                    await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
                    logger.info(f"[LinkedIn] Page loaded: {page.url}")
                except Exception as e:
                    logger.error(f"[LinkedIn] Navigation timeout/error: {e}")
                    await browser.close()
                    return None
                
                # Human-like pacing
                await _human_delay(3.0, 6.0)
                await _human_scroll(page, rounds=2, px=500)
                await _human_click_more(page)
                await _human_delay(1.0, 2.0)

                # Log all H2s to see if we are on the right page
                try:
                    h2s = await page.query_selector_all("h2")
                    h2_texts = [await h2.inner_text() for h2 in h2s]
                    logger.info(f"[LinkedIn] Found H2s: {h2_texts}")
                except Exception:
                    pass

                # Try several common selectors for the job description, 
                # prioritizing the most robust ones first.
                selectors = [
                    "[data-testid='expandable-text-box']",
                    "[data-sdui-component*='aboutTheJob']",
                    "article",
                    ".jobs-description__content",
                    ".jobs-box__html-content",
                    ".jobs-description-content__text",
                    ".show-more-less-html__markup",
                    ".jobs-description",
                    "section.jobs-description",
                    ".description__text"
                ]
                
                content = None
                for selector in selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        logger.info(f"[LinkedIn] Selector '{selector}' found {len(elements)} elements")
                        for el in elements:
                            text = await el.inner_text()
                            if text and len(text.strip()) > 200:
                                content = text.strip()
                                logger.info(f"[LinkedIn] Extracted content using selector: {selector} ({len(content)} chars)")
                                break
                        if content: break
                    except Exception as e:
                        logger.warning(f"[LinkedIn] Error with selector '{selector}': {e}")
                        continue
                
                # Fallback 1: Search for "About the job" heading if selectors fail
                if not content:
                    logger.info("[LinkedIn] No content found via selectors, trying text search fallback...")
                    try:
                        h2s = await page.query_selector_all("h2")
                        for h2 in h2s:
                            h2_text = await h2.inner_text()
                            if "About the job" in h2_text or "About the Job" in h2_text:
                                parent = await h2.query_selector("xpath=..")
                                if parent:
                                    parent_text = await parent.inner_text()
                                    if len(parent_text) > 200:
                                        content = parent_text
                                        logger.info("[LinkedIn] Extracted via 'About the job' text search fallback")
                                        break
                    except Exception as e:
                        logger.error(f"[LinkedIn] Fallback search error: {e}")

                # Fallback 2: Full page body text — strip short nav lines, keep substance
                if not content:
                    logger.info("[LinkedIn] Trying full-page body text fallback...")
                    try:
                        body_text = await page.inner_text("body")
                        if body_text and len(body_text.strip()) > 500:
                            lines = [l.strip() for l in body_text.split('\n') if len(l.strip()) > 30]
                            candidate = '\n'.join(lines)
                            if len(candidate) > 300:
                                content = candidate[:5000]
                                logger.info(f"[LinkedIn] Extracted via body text fallback ({len(content)} chars)")
                    except Exception as e:
                        logger.error(f"[LinkedIn] Body text fallback error: {e}")

                await browser.close()
                
                if content:
                    content = content.strip()
                    logger.info(f"[LinkedIn] Successfully fetched JD ({len(content)} chars)")
                    return content
                
                logger.warning(f"[LinkedIn] Failed to extract JD text from {job_url}")
                return None

        except Exception as e:
            logger.error(f"[LinkedIn] Error fetching JD for user {user_id}: {e}")
            return None
