import asyncio
import os
import sys
import json
from dotenv import load_dotenv
load_dotenv(override=True)
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, LinkedInSession, User, JobApplication, JobOpportunity, AutoApplyCredential, UserProfile
from agents.auto_apply_agent import AutoApplyAgent, _run_playwright_in_thread
from app.utils.security import encrypt_value, decrypt_value

async def test_injection():
    db = SessionLocal()
    try:
        # 1. Find a user with a LinkedIn session (or create mock)
        user = db.query(User).first()
        if not user:
            print("No user found in DB.")
            return

        session = db.query(LinkedInSession).filter(LinkedInSession.user_id == user.id).first()
        if not session or not session.cookies_enc:
            print(f"User {user.email} has no LinkedIn session. Cannot test login bypass.")
            return

        cookies = json.loads(decrypt_value(session.cookies_enc))
        print(f"Testing session injection for {user.email} with {len(cookies)} cookies.")

        # 2. Mock app_data
        app_data = {
            "url": "https://www.linkedin.com/jobs/view/3858348937/", # Just a random job
            "email": user.email,
            "first_name": "Test",
            "last_name": "User",
            # Add other required fields
        }

        # 3. Run Playwright in thread (simulated)
        # Note: We use a small max_steps or just check initial navigation
        print("Launching browser to verify session...")
        
        # We manually call _run_playwright_in_thread logic or a subset
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            profile_dir = os.path.join(os.getcwd(), "browser_profiles", "test_injection")
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            # Inject
            await context.add_cookies(cookies)
            
            page = context.pages[0]
            print(f"Navigating to LinkedIn Feed...")
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            await asyncio.sleep(8) # Wait for hydration
            
            # Take screenshot
            await page.screenshot(path="scratch/session_test.png")
            print("Screenshot saved to scratch/session_test.png")
            
            # Check for various logged-in indicators
            nav = await page.query_selector('.global-nav__me, [data-test-id="global-nav"], .share-box-feed-entry__trigger')
            if nav:
                print("SUCCESS: Session injected and detected on LinkedIn!")
            else:
                print("FAILURE: Session not detected. Page Title:", await page.title())
                if "Login" in await page.title() or "Sign In" in await page.title():
                    print("Status: Redirected to Login page.")
                
            await context.close()

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_injection())
