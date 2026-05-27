#!/usr/bin/env python3
"""
Upload a document to the Career Revolution API.
"""

import requests
import json
import os

BASE_URL = "http://localhost:8000"

def get_token():
    """Login and return JWT token."""
    login_data = {
        "username": "rajeev.sharma@mail.ch",
        "password": "SecurePass123"
    }
    try:
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        response.raise_for_status()
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Login failed: {e}")
        return None

def upload_document(token: str, file_path: str, document_type: str = "resume"):
    """Upload a document to the API."""
    print(f"\nUploading {file_path} as {document_type}...")
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "text/plain")}
        data = {"document_type": document_type}
        
        try:
            response = requests.post(f"{BASE_URL}/documents/upload", headers=headers, files=files, data=data)
            response.raise_for_status()
            print("[OK] Document uploaded successfully!")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"✗ Document upload failed: {e}")
            if response.status_code:
                print(f"  Status Code: {response.status_code}")
                print(f"  Response: {response.text}")
            return None

def main():
    token = get_token()
    if not token:
        print("Exiting due to login failure.")
        return
    
    # Path to the new test resume
    resume_path = "test_resume_with_linkedin.txt"
    
    # Upload the document
    upload_result = upload_document(token, resume_path, document_type="resume")
    
    if upload_result:
        print(f"Uploaded document ID: {upload_result['id']}")
    
if __name__ == "__main__":
    main()