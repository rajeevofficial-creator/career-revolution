"""Test LinkedIn login with fixed selectors."""
import asyncio, logging, sys
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])

async def main():
    from app.models.database import SessionLocal
    from app.services.linkedin_browser import LinkedInBrowserService

    db = SessionLocal()
    svc = LinkedInBrowserService()

    svc.save_credentials(db, user_id=1, email="mashu786@yahoo.com", password="Basel123@")
    print("Credentials saved. Attempting login...")

    success, message = await svc.login(db, user_id=1)
    print(f"\nResult  : {'SUCCESS' if success else 'FAILED'}")
    print(f"Message : {message}")

    if success:
        status = svc.session_status(db, user_id=1)
        print(f"Status  : {status}")

    db.close()

asyncio.run(main())
