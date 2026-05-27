"""Simulate server-side LinkedIn login to expose real error."""
import asyncio, logging, traceback, sys, os
# Load .env manually
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s")

async def main():
    from app.models.database import SessionLocal, LinkedInSession
    from app.utils.security import encrypt_value, decrypt_value

    EMAIL = "mashu786@yahoo.com"
    PASSWORD = "Basel123@"

    db = SessionLocal()

    # Step 1: save credentials
    row = db.query(LinkedInSession).filter(LinkedInSession.user_id == 1).first()
    if not row:
        from app.models.database import LinkedInSession as LS
        row = LS(user_id=1)
        db.add(row)
    row.linkedin_email_enc = encrypt_value(EMAIL)
    row.linkedin_pw_enc = encrypt_value(PASSWORD)
    row.is_valid = False
    db.commit()
    print(f"Credentials saved. Email decrypts to: {decrypt_value(row.linkedin_email_enc)}")

    # Step 2: attempt login step by step
    from playwright.async_api import async_playwright
    import random

    async def human_delay(lo=1.2, hi=3.0):
        await asyncio.sleep(random.uniform(lo, hi))

    STEALTH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-infobars",
        "--lang=en-US,en",
    ]
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    try:
        async with async_playwright() as pw:
            print("Launching browser...")
            browser = await pw.chromium.launch(headless=True, args=STEALTH_ARGS)
            ctx = await browser.new_context(user_agent=UA, viewport={"width":1280,"height":900},
                                             locale="en-US", timezone_id="Europe/Zurich")
            await ctx.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
            page = await ctx.new_page()

            print("Navigating to LinkedIn login...")
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
            print(f"Page title: {await page.title()}")
            print(f"URL: {page.url}")
            await human_delay(1.5, 2.5)

            print("Filling email...")
            await page.fill('input[name="session_key"]', EMAIL)
            await human_delay(0.5, 1.0)

            print("Filling password...")
            await page.fill('input[name="session_password"]', PASSWORD)
            await human_delay(0.8, 1.5)

            print("Clicking sign in...")
            await page.click('button[type="submit"]')
            await human_delay(3.0, 5.0)

            print(f"After login URL: {page.url}")
            print(f"After login title: {await page.title()}")

            # Check for challenges
            if "checkpoint" in page.url or "challenge" in page.url:
                print("CHALLENGE/2FA DETECTED")
            elif "feed" in page.url or "mynetwork" in page.url or "jobs" in page.url:
                print("LOGIN SUCCESSFUL!")
                cookies = await ctx.cookies()
                print(f"Got {len(cookies)} cookies")
            else:
                # Check for error on page
                content = await page.content()
                error_idx = content.find("error")
                if error_idx > 0:
                    print("Error snippet:", content[max(0,error_idx-50):error_idx+200])
                print("Login status unclear — check URL above")

            await browser.close()
    except Exception as e:
        print(f"\nEXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        db.close()

asyncio.run(main())
