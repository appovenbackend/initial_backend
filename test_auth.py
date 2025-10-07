#!/usr/bin/env python3
"""
Authentication Testing Script
Run this script to test and debug authentication issues step by step.
"""

import requests
import json
import sys

# Configuration
BASE_URL = "https://initialbackend-production.up.railway.app/"  # Change this to your server URL

def test_endpoint(endpoint, method="GET", headers=None, data=None):
    """Test an endpoint and return the response"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n🧪 Testing {method} {url}")

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            print(f"❌ Unsupported method: {method}")
            return None

        print(f"Status Code: {response.status_code}")

        if response.headers.get('content-type', '').startswith('application/json'):
            response_data = response.json()
            print(f"Response: {json.dumps(response_data, indent=2)}")
        else:
            print(f"Response: {response.text}")

        return response

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def main():
    print("🔐 Authentication Debugging Script")
    print("=" * 50)

    # Test 1: Basic connectivity
    print("\n1️⃣ Testing basic connectivity...")
    response = test_endpoint("/test")
    if not response or response.status_code != 200:
        print("❌ Basic connectivity test failed. Make sure your server is running.")
        return

    # Test 2: Authentication debugging endpoint
    print("\n2️⃣ Testing auth debugging endpoint (without token)...")
    response = test_endpoint("/auth-test")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Auth test endpoint accessible: {data.get('authenticated', False)}")

    # Test 3: Try to login and get a token
    print("\n3️⃣ Testing login to get JWT token...")
    login_data = {
        "phone": input("Enter phone number: "),
        "password": input("Enter password: ")
    }

    response = test_endpoint("/auth/login", method="POST", data=login_data)

    if response and response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        user_id = data.get("user", {}).get("id")

        if token:
            print(f"✅ Login successful! Token: {token[:50]}...")
            print(f"User ID: {user_id}")

            # Test 4: Use token to access protected endpoint
            print("\n4️⃣ Testing protected endpoint with token...")
            headers = {"Authorization": f"Bearer {token}"}
            response = test_endpoint("/auth-test", headers=headers)

            if response and response.status_code == 200:
                data = response.json()
                if data.get("authenticated"):
                    print(f"✅ Authentication working! User: {data.get('user_id')}")
                else:
                    print("❌ Token not working - check middleware configuration")
            else:
                print("❌ Protected endpoint failed - check token format and middleware")

            # Test 5: Test profile endpoint
            print("\n5️⃣ Testing profile endpoint...")
            response = test_endpoint("/auth/me", headers=headers)

            if response and response.status_code == 200:
                print("✅ Profile endpoint working!")
            else:
                print("❌ Profile endpoint failed")

        else:
            print("❌ No token received from login")
    else:
        print("❌ Login failed - check credentials or server configuration")

    print("\n" + "=" * 50)
    print("🔍 Debugging complete!")
    print("\nCommon issues to check:")
    print("1. JWT_SECRET environment variable consistency")
    print("2. Authorization header format: 'Bearer <token>'")
    print("3. Token expiration (default: 120 minutes)")
    print("4. CORS configuration allowing Authorization header")
    print("5. Middleware order in main.py")

if __name__ == "__main__":
    main()
