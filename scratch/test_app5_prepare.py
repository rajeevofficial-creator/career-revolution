import asyncio
import json
import logging
import os
import sys
import requests

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from app.models.database import SessionLocal, User
from app.utils.security import decrypt_value

def test_live_prepare():
    db = SessionLocal()
    try:
        # Get password for user 1 from DB
        from sqlalchemy import text
        cursor = db.execute(text("SELECT email_password_enc FROM auto_apply_credentials WHERE user_id = 1"))
        row = cursor.fetchone()
        if not row:
            print("No credentials found")
            return
            
        password = "demo123"
        user = db.query(User).filter(User.id == 1).first()
        email = user.email
        
        print(f"Logging in as {email} to get auth token...")
        
        # Authenticate on the running server (port 8010)
        # Note: OAuth2PasswordRequestForm expects username and password form fields
        login_res = requests.post(
            "http://localhost:8010/auth/login",
            data={"username": email, "password": password}
        )
        
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.status_code} - {login_res.text}")
            return
            
        token_data = login_res.json()
        token = token_data["access_token"]
        print("Login successful! Got access token.")
        
        # Trigger prepare on app ID 6
        print("Triggering prepare for application 6 on live server...")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Wait up to 180s for Playwright + LLM refinement loop to complete
        prepare_res = requests.post(
            "http://localhost:8010/applications/6/prepare",
            headers=headers,
            timeout=180
        )
        
        print(f"Status Code: {prepare_res.status_code}")
        print("Response:")
        try:
            print(json.dumps(prepare_res.json(), indent=2))
        except Exception:
            print(prepare_res.text)
            
    finally:
        db.close()

if __name__ == "__main__":
    test_live_prepare()
