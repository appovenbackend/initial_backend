#!/usr/bin/env python3
"""
Remote Authentication Testing Script
Tests authentication against the Railway deployment
"""

import requests
import json

# Your Railway deployment URL
BASE_URL = "https://initialbackend-production.up.railway.app"

def test_authentication():
    print("🔐 Testing Authentication Against Railway Deployment")
    print("=" * 60)

    # Test 1: Basic connectivity
    print("\n1️⃣ Testing basic connectivity...")
    try:
        response = requests.get(f"{BASE_URL}/test")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Server is responding")
        else:
            print(f"❌ Server error: {response.text}")
            return
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    # Test 2: Login to get token
    print("\n2️⃣ Testing login...")
    login_data = {
        "phone": "+919999999999",
        "password": "securepassword123"
    }

    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Login Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"✅ Login successful! Token: {token[:50]}...")

            # Test 3: Use token for protected endpoint
            print("\n3️⃣ Testing protected endpoint with token...")
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
            print(f"Profile Status Code: {response.status_code}")

            if response.status_code == 200:
                print("✅ Authentication working perfectly!")
                print(f"User data: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"❌ Authentication failed: {response.text}")

                # Check if it's a middleware issue
                if response.status_code == 401:
                    print("\n🔍 Debugging middleware issue...")

                    # Test if the issue is with request.state not being set
                    # by checking the error response format
                    try:
                        error_data = response.json()
                        if "JWT middleware did not set user_id" in error_data.get("detail", ""):
                            print("✅ Enhanced error message detected - our fix is working!")
                            print("❌ But the middleware is still not setting user_id properly")
                        else:
                            print("❌ Standard 401 error - middleware may not be running")
                    except:
                        print("❌ Could not parse error response")

        else:
            print(f"❌ Login failed: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {e}")

    print("\n" + "=" * 60)
    print("🔍 Analysis:")
    print("If login works but protected endpoints fail with 401,")
    print("the issue is likely that the JWT middleware changes")
    print("haven't been deployed to Railway yet.")
    print("\nTo fix: Deploy your updated code to Railway.")

if __name__ == "__main__":
    test_authentication()
