#!/usr/bin/env python3
"""
Deployment Fix Script
This script helps deploy the database fix to Railway without shell access.
"""

import requests
import json
import sys

# Your Railway app URL
RAILWAY_APP_URL = "https://initialbackend-production.up.railway.app"

def check_migration_status():
    """Check the current migration status."""
    try:
        response = requests.get(f"{RAILWAY_APP_URL}/migration/status")
        return response.json()
    except Exception as e:
        print(f"❌ Failed to check migration status: {e}")
        return None

def fix_database():
    """Apply the database fix via HTTP endpoint."""
    try:
        print("🔄 Attempting to fix database via HTTP endpoint...")
        response = requests.post(f"{RAILWAY_APP_URL}/migration/fix-registration-link")

        if response.status_code == 200:
            result = response.json()
            print("✅ Database fix successful!")
            print(f"   Status: {result.get('status')}")
            print(f"   Message: {result.get('message')}")
            return True
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

def test_events_endpoint():
    """Test if the events endpoint works after the fix."""
    try:
        print("🔄 Testing events endpoint...")
        response = requests.get(f"{RAILWAY_APP_URL}/events/")

        if response.status_code == 200:
            events = response.json()
            print("✅ Events endpoint working!")
            print(f"   Found {len(events)} events")
            return True
        else:
            print(f"❌ Events endpoint still failing: {response.status_code}")
            print(f"   Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Failed to test events endpoint: {e}")
        return False

def main():
    print("🚀 Railway Database Fix Tool")
    print("============================")

    # Check current status
    print("\n📊 Checking current migration status...")
    status = check_migration_status()

    if status:
        print(f"   Registration link column exists: {status.get('registration_link_column_exists', False)}")
        print(f"   Status: {status.get('status', 'unknown')}")

        if status.get('registration_link_column_exists'):
            print("\n✅ Database is already fixed!")
            return True

    # Apply the fix
    print("\n🔧 Applying database fix...")
    fix_success = fix_database()

    if not fix_success:
        print("\n❌ Database fix failed!")
        print("   The migration endpoint might not be available yet.")
        print("   Try redeploying your Railway app first.")
        return False

    # Wait a moment for the fix to take effect
    print("\n⏳ Waiting for fix to take effect...")
    import time
    time.sleep(3)

    # Test the events endpoint
    print("\n🧪 Testing events endpoint...")
    test_success = test_events_endpoint()

    if test_success:
        print("\n🎉 SUCCESS! Your database is fixed and API is working!")
        print("   You can now use all events functionality including registration links.")
    else:
        print("\n⚠️  Fix applied but events endpoint still has issues.")
        print("   This might be a temporary issue. Try again in a few minutes.")

    return test_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
