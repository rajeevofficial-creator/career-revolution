"""Test LinkedIn login directly to expose the real error."""
import asyncio, logging, sys
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(name)s: %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])

async def main():
    from app.models.database import SessionLocal
    from app.services.linkedin_browser import LinkedInBrowserService

    db = SessionLocal()
    svc = LinkedInBrowserService()

    # Use real credentials
    EMAIL = "mashu786@yahoo.com"
    PASSWORD = input("Enter LinkedIn password: ").strip()

    print("\n--- Saving credentials ---")
    svc.save_credentials(db, user_id=1, email=EMAIL, password=PASSWORD)

    print("\n--- Attempting login ---")
    try:
        success, message = await svc.login(db, user_id=1)
        print(f"Success: {success}")
        print(f"Message: {message}")
    except Exception as e:
        import traceback
        print(f"\nEXCEPTION: {e}")
        traceback.print_exc()
    finally:
        db.close()

asyncio.run(main())
