import asyncio
import json
import logging
import os
import sys

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

# Configure logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

from app.models.database import SessionLocal, JobApplication, User
from app.main import prepare_application_materials

async def run_test():
    db = SessionLocal()
    try:
        # Get user 1
        user = db.query(User).filter(User.id == 1).first()
        if not user:
            print("User 1 not found")
            return
            
        print(f"Running prepare_application_materials for app 4 and user {user.email}")
        
        # Call the endpoint function directly
        # Since prepare_application_materials is async, we await it.
        # Note: in main.py, it takes id, body, current_user, db
        try:
            result = await prepare_application_materials(
                id=4,
                body=None,
                current_user=user,
                db=db
            )
            print("SUCCESS! Result:")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print("EXCEPTION raised during endpoint execution:")
            import traceback
            traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_test())
