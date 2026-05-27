import time
import requests
import json

BASE_URL = "http://localhost:8005"
USERNAME = "rajeev.sharma@mail.ch"
PASSWORD = "password"

def run_test():
    print("Testing /auth/login...")
    start = time.time()
    try:
        res = requests.post(f"{BASE_URL}/auth/login", data={'username': USERNAME, 'password': PASSWORD}, timeout=15)
        print(f"Login Time: {time.time() - start:.3f}s | Status: {res.status_code}")
        if res.status_code != 200:
            print("Login failed:", res.text)
            return
        token = res.json().get('access_token')
    except Exception as e:
        print(f"Login error: {e}")
        return

    headers = {'Authorization': f'Bearer {token}'}

    print("Testing /dashboard...")
    start = time.time()
    try:
        res2 = requests.get(f"{BASE_URL}/dashboard", headers=headers, timeout=15)
        print(f"Dashboard Time: {time.time() - start:.3f}s | Status: {res2.status_code}")
    except Exception as e:
        print(f"Dashboard error: {e}")

    print("Testing /jobs/search...")
    start = time.time()
    try:
        res3 = requests.get(f"{BASE_URL}/jobs/search", headers=headers, timeout=15)
        print(f"Jobs Search Time: {time.time() - start:.3f}s | Status: {res3.status_code}")
    except Exception as e:
        print(f"Jobs search error: {e}")

if __name__ == "__main__":
    run_test()
