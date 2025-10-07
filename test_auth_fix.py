#!/usr/bin/env python3
"""
Test script to verify JWT authentication fix
"""
import requests
import json
import sys

# Configuration
BASE_URL = "https://initialbackend-production.up.railway.app"
# BASE_URL = "http://localhost:8000"  # Use for local testing

def test_login_and_me():
    """Test login followed by /auth/me endpoint"""
    print("🔐 Testing JWT authentication fix...")

    # Test data - you'll need to replace with actual credentials
    login_data = {
        "phone": "1234567890",  # Replace with actual phone number
        "password": "password123"  # Replace with actual password
    }

    try:
        # Step 1: Login to get JWT token
        print(f"📱 Attempting login for phone: {login_data['phone']}")
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=10)

        print(f"Login status: {login_response.status_code}")

        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.text}")
            return False

        login_result = login_response.json()
        access_token = login_result.get("access_token")

        if not access_token:
            print("❌ No access token in login response")
            return False

        print(f"✅ Login successful, got token: {access_token[:20]}...")

        # Step 2: Test /auth/me endpoint with JWT token
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        print("👤 Testing /auth/me endpoint...")
        me_response = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)

        print(f"/auth/me status: {me_response.status_code}")

        if me_response.status_code == 200:
            me_result = me_response.json()
            print(f"✅ /auth/me successful! User: {me_result.get('name')} (ID: {me_result.get('id')})")
            return True
        else:
            print(f"❌ /auth/me failed: {me_response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_auth_test_endpoint():
    """Test the /auth-test endpoint for debugging"""
    print("\n🔧 Testing /auth-test endpoint...")

    try:
        response = requests.get(f"{BASE_URL}/auth-test", timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Auth test successful!")
            print(f"   Authenticated: {result.get('authenticated')}")
            print(f"   User ID: {result.get('user_id')}")
            print(f"   User Role: {result.get('user_role')}")
            return result.get('authenticated', False)
        else:
            print(f"❌ Auth test failed: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Auth test error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting JWT authentication fix verification...\n")

    # Test 1: Check auth-test endpoint (doesn't require authentication)
    auth_test_works = test_auth_test_endpoint()

    # Test 2: Test full login -> /auth/me flow
    login_flow_works = test_login_and_me()

    print("\n📊 Test Results:")
    print(f"   Auth test endpoint: {'✅ PASS' if auth_test_works else '❌ FAIL'}")
    print(f"   Login + /auth/me flow: {'✅ PASS' if login_flow_works else '❌ FAIL'}")

    if login_flow_works:
        print("\n🎉 JWT authentication fix is working correctly!")
        print("   The /auth/me endpoint should now properly authenticate users.")
    else:
        print("\n⚠️  There may still be issues with JWT authentication.")
        print("   Please check the server logs for more details.")

    sys.exit(0 if login_flow_works else 1)
