import os
import sys
import time
import requests

sys.path.append('c:/Users/rajeev/career_revolution')

from sqlalchemy.orm import Session
from app.models.database import SessionLocal, User
from app.services.auth import create_access_token

def test():
    db = SessionLocal()
    user = db.query(User).filter(User.email == 'rajeev.sharma@mail.ch').first()
    if not user:
        print("User not found!")
        return
    token = create_access_token({"sub": user.email, "user_id": user.id})
    db.close()

    print(f"Generated Token: {token[:10]}...")

    headers = {'Authorization': f'Bearer {token}'}

    print("Testing /dashboard...")
    start = time.time()
    try:
        res = requests.get("http://localhost:8005/dashboard", headers=headers, timeout=5)
        print(f"Dashboard: {res.status_code} in {time.time()-start:.3f}s")
    except Exception as e:
        print(f"Dashboard error: {e}")

    print("Testing /jobs/search...")
    start = time.time()
    try:
        res2 = requests.get("http://localhost:8005/jobs/search", headers=headers, timeout=5)
        print(f"Jobs/Search: {res2.status_code} in {time.time()-start:.3f}s")
    except Exception as e:
        print(f"Jobs/search error: {e}")

if __name__ == "__main__":
    test()
