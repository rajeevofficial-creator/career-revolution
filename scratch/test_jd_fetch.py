
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import SessionLocal, LinkedInSession
from app.services.linkedin_browser import LinkedInBrowserService, _STEALTH_ARGS, _USER_AGENT, _STEALTH_INIT_SCRIPT
from playwright_stealth import Stealth
_stealth = Stealth()
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

async def test_fetch_jd(job_url):
    db = SessionLocal()
    try:
        user_id = 1
        row = db.query(LinkedInSession).filter(LinkedInSession.user_id == user_id).first()
        if not row:
            print("No session found")
            return

        from app.services.linkedin_browser import decrypt_value
        cookies = json.loads(decrypt_value(row.cookies_enc))

        from app.services.linkedin_browser import LinkedInBrowserService
        service = LinkedInBrowserService()
        
        print(f"Calling service.fetch_job_description for {job_url}...")
        
        # We need to see the page to find buttons, so let's do a manual fetch here 
        # to inspect the DOM while we're at it.
        from playwright.async_api import async_playwright
        from app.services.linkedin_browser import _STEALTH_ARGS, _USER_AGENT, _STEALTH_INIT_SCRIPT
        import playwright_stealth as _stealth

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=_STEALTH_ARGS)
            ctx = await browser.new_context(user_agent=_USER_AGENT)
            await ctx.add_init_script(_STEALTH_INIT_SCRIPT)
            await ctx.add_cookies(cookies)
            page = await ctx.new_page()
            
            # Use the service's own stealth setup
            await ctx.add_init_script(_STEALTH_INIT_SCRIPT)
            
            print(f"Navigating to {job_url}...")
            await page.goto(job_url, wait_until="domcontentloaded")
            await asyncio.sleep(5)
            
            print("Dumping ALL interactive elements for debug...")
            elements = await page.query_selector_all("button, a")
            for i, el in enumerate(elements):
                tag = await el.evaluate("node => node.tagName")
                text = (await el.inner_text()).strip()
                aria = (await el.get_attribute("aria-label") or "").strip()
                href = (await el.get_attribute("href") or "").strip()
                if text or aria:
                    print(f"Element {i}: Tag={tag} Text='{text}' Aria='{aria}' Href='{href[:50]}'")

            await browser.close()
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.linkedin.com/jobs/view/4408244282/"
    asyncio.run(test_fetch_jd(url))
