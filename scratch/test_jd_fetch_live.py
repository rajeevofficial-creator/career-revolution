import asyncio
import json
import logging
import os
import sys

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_jd_fetch_live")

from app.models.database import SessionLocal, LinkedInSession
from app.services.linkedin_browser import LinkedInBrowserService, _STEALTH_ARGS, _USER_AGENT, _STEALTH_INIT_SCRIPT, _human_delay, _human_scroll, _human_click_more
from app.utils.security import decrypt_value
from playwright_stealth import Stealth
_stealth = Stealth()

async def run_test():
    db = SessionLocal()
    try:
        user_id = 1
        job_url = "https://www.linkedin.com/jobs/view/4415358765/"
        
        row = db.query(LinkedInSession).filter(LinkedInSession.user_id == user_id).first()
        if not row:
            logger.error("No LinkedInSession found in DB for user 1")
            return
        
        logger.info(f"LinkedInSession found. Valid: {row.is_valid}")
        if not row.cookies_enc:
            logger.error("No cookies stored in DB")
            return
            
        cookies = json.loads(decrypt_value(row.cookies_enc))
        logger.info(f"Loaded {len(cookies)} cookies.")

        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            logger.info("Launching chromium...")
            browser = await pw.chromium.launch(headless=True, args=_STEALTH_ARGS)
            ctx = await browser.new_context(
                user_agent=_USER_AGENT,
                viewport={"width": 1280, "height": 900},
                locale="en-US",
            )
            await ctx.add_init_script(_STEALTH_INIT_SCRIPT)
            await ctx.add_cookies(cookies)
            page = await ctx.new_page()
            await _stealth.apply_stealth_async(page)

            logger.info(f"Navigating to {job_url}...")
            try:
                await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
                logger.info(f"Page loaded: {page.url}")
            except Exception as e:
                logger.error(f"Navigation error: {e}")
                await page.screenshot(path="scratch/li_fetch_err_nav.png")
                await browser.close()
                return

            await page.screenshot(path="scratch/li_fetch_1_loaded.png")
            logger.info("Screenshot saved: scratch/li_fetch_1_loaded.png")

            # Try to get H2s
            try:
                h2s = await page.query_selector_all("h2")
                h2_texts = [await h2.inner_text() for h2 in h2s]
                logger.info(f"Found H2s: {h2_texts}")
            except Exception as e:
                logger.error(f"Error querying H2s: {e}")

            # Run human delays & scrolls
            logger.info("Running human delay/scroll/click_more...")
            await _human_delay(3.0, 5.0)
            await _human_scroll(page, rounds=2, px=500)
            await page.screenshot(path="scratch/li_fetch_2_scrolled.png")
            logger.info("Screenshot saved: scratch/li_fetch_2_scrolled.png")

            # Try click more
            try:
                await _human_click_more(page)
                logger.info("Clicked 'show more' if found.")
            except Exception as e:
                logger.error(f"Error clicking more: {e}")
            await _human_delay(1.0, 2.0)
            await page.screenshot(path="scratch/li_fetch_3_clicked.png")
            logger.info("Screenshot saved: scratch/li_fetch_3_clicked.png")

            # Selectors
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
                    logger.info(f"Selector '{selector}' found {len(elements)} elements")
                    for idx, el in enumerate(elements):
                        text = await el.inner_text()
                        logger.info(f"  Element {idx} length: {len(text) if text else 0}")
                        if text and len(text.strip()) > 200:
                            content = text.strip()
                            logger.info(f"  -> MATCHED using selector: {selector} ({len(content)} chars)")
                            break
                    if content:
                        break
                except Exception as e:
                    logger.warning(f"Error with selector '{selector}': {e}")
            
            if not content:
                logger.info("Trying text search fallback...")
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
                                    logger.info("Matched via 'About the job' parent text")
                                    break
                except Exception as e:
                    logger.error(f"Fallback error: {e}")

            if content:
                logger.info(f"JD successfully fetched! Prefix: {content[:200]}")
            else:
                logger.error("JD fetch failed!")

            await browser.close()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_test())
