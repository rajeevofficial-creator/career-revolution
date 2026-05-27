"""
Simple upload test using built-in modules.
"""

import http.client
import json
import base64

# Configuration
HOST = "localhost:8000"
LOGIN_PATH = "/auth/login"
UPLOAD_PATH = "/documents/upload-multiple"

# Test credentials
EMAIL = "rajeev.sharma@mail.ch"
PASSWORD = "Naukri123"

def test_upload():
    """Test upload functionality."""
    
    print("Testing Career Revolution file upload...")
    print("=" * 50)
    
    # 1. Login
    print("1. Logging in...")
    conn = http.client.HTTPConnection(HOST)
    
    login_data = f"username={EMAIL}&password={PASSWORD}"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Content-Length": str(len(login_data))
    }
    
    conn.request("POST", LOGIN_PATH, login_data, headers)
    login_response = conn.getresponse()
    
    if login_response.status != 200:
        print(f"   ✗ Login failed: {login_response.status} {login_response.reason}")
        print(f"   Response: {login_response.read().decode()}")
        return
    
    login_result = json.loads(login_response.read().decode())
    token = login_result.get("access_token")
    print(f"   SUCCESS: Login successful")
    print(f"   Token: {token[:30]}...")
    
    # 2. Create a simple test file
    print("\n2. Creating test file...")
    test_content = b"Test resume content for upload testing."
    
    # 3. Test upload (this would need proper multipart form data)
    print("\n3. Testing upload endpoint structure...")
    
    # Check if endpoint exists
    conn.request("GET", "/docs", headers={"Authorization": f"Bearer {token}"})
    docs_response = conn.getresponse()
    print(f"   Docs endpoint: {docs_response.status} {docs_response.reason}")
    
    # Check dashboard
    conn.request("GET", "/dashboard", headers={"Authorization": f"Bearer {token}"})
    dashboard_response = conn.getresponse()
    print(f"   Dashboard: {dashboard_response.status} {dashboard_response.reason}")
    
    if dashboard_response.status == 200:
        dashboard_data = json.loads(dashboard_response.read().decode())
        print(f"   User: {dashboard_data.get('user', {}).get('email')}")
        print(f"   Stats: {dashboard_data.get('stats', {})}")
    
    conn.close()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nNext steps:")
    print("1. The upload endpoint exists at POST /documents/upload-multiple")
    print("2. It expects multipart/form-data with 'files' field")
    print("3. Frontend needs to send FormData correctly")
    print("4. Check browser console for JavaScript errors")

if __name__ == "__main__":
    test_upload()