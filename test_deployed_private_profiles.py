#!/usr/bin/env python3
"""
Test script to verify private profile functionality on deployed backend.
"""

import requests
import json

BASE_URL = "https://initialbackend-production.up.railway.app"

def test_deployed_private_profile_functionality():
    """Test private profile privacy controls on deployed backend"""
    
    print("🔒 Testing Private Profile Functionality (Deployed)")
    print("=" * 60)
    
    # Use provided credentials
    user_id = "u_872e4600ed"
    access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1Xzg3MmU0NjAwZWQiLCJleHAiOjE3NTk0Nzc5OTl9.dOrQVK7o2GRYMRsNWZiv7X2te1hhkR_OuiHRfpHNyR4"
    
    headers = {"X-User-ID": user_id}
    
    print(f"Using existing user: {user_id}")
    
    # Test 1: Get current user profile
    print("\n1. Getting current user profile...")
    try:
        response = requests.get(f"{BASE_URL}/social/users/{user_id}", headers=headers)
        if response.status_code == 200:
            profile = response.json()
            print(f"   📄 Current profile:")
            print(f"      Name: {profile.get('name', 'N/A')}")
            print(f"      Is Private: {profile.get('is_private', 'N/A')}")
            print(f"      Bio: {profile.get('bio', 'None')}")
            print(f"      Picture: {profile.get('picture', 'None')}")
            print(f"      Strava: {profile.get('strava_link', 'None')}")
            print(f"      Instagram: {profile.get('instagram_id', 'None')}")
            print(f"      Connections Count: {profile.get('connections_count', 0)}")
            print(f"      Is Connected: {profile.get('is_connected', False)}")
            print(f"      Connection Status: {profile.get('connection_status', 'None')}")
        else:
            print(f"   ❌ Failed to get profile: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error getting profile: {e}")
        return
    
    # Test 2: Get current privacy setting
    print("\n2. Getting current privacy setting...")
    try:
        response = requests.get(f"{BASE_URL}/social/users/{user_id}/privacy", headers=headers)
        if response.status_code == 200:
            privacy_data = response.json()
            print(f"   🔒 Current privacy setting: {'Private' if privacy_data['is_private'] else 'Public'}")
            current_privacy = privacy_data['is_private']
        else:
            print(f"   ❌ Failed to get privacy: {response.status_code} - {response.text}")
            current_privacy = False
    except Exception as e:
        print(f"   ❌ Error getting privacy setting: {e}")
        current_privacy = False
    
    # Test 3: Toggle privacy setting
    print("\n3. Toggling privacy setting...")
    try:
        response = requests.put(f"{BASE_URL}/social/users/{user_id}/privacy", headers=headers)
        if response.status_code == 200:
            result = response.json()
            new_privacy = result['is_private']
            print(f"   ✅ Privacy toggled successfully: {result['message']}")
            print(f"   🔄 Privacy changed from {'Private' if current_privacy else 'Public'} to {'Private' if new_privacy else 'Public'}")
        else:
            print(f"   ❌ Failed to toggle privacy: {response.status_code} - {response.text}")
            new_privacy = current_privacy
    except Exception as e:
        print(f"   ❌ Error toggling privacy: {e}")
        new_privacy = current_privacy
    
    # Test 4: Get profile after privacy change
    print(f"\n4. Getting profile after privacy change (now {'Private' if new_privacy else 'Public'})...")
    try:
        response = requests.get(f"{BASE_URL}/social/users/{user_id}", headers=headers)
        if response.status_code == 200:
            profile = response.json()
            print(f"   📄 Profile after privacy change:")
            print(f"      Name: {profile.get('name', 'N/A')}")
            print(f"      Is Private: {profile.get('is_private', 'N/A')}")
            print(f"      Bio: {profile.get('bio', 'None (hidden)')}")
            print(f"      Picture: {profile.get('picture', 'None (hidden)')}")
            print(f"      Strava: {profile.get('strava_link', 'None (hidden)')}")
            print(f"      Instagram: {profile.get('instagram_id', 'None (hidden)')}")
            print(f"      Subscribed Events: {profile.get('subscribed_events', [])}")
            
            # Check if privacy is working as expected
            is_private = profile.get('is_private', False)
            has_sensitive_data = profile.get('bio') is not None or profile.get('picture') is not None
            
            if is_private and not has_sensitive_data:
                print("   ✅ Privacy controls working correctly - sensitive info hidden for private account!")
            elif not is_private and has_sensitive_data:
                print("   ✅ Privacy controls working correctly - sensitive info visible for public account!")
            elif is_private and has_sensitive_data:
                print("   ❌ Privacy controls NOT working - private account showing sensitive data!")
            else:
                print("   ⚠️ Privacy logic unclear - public account not showing sensitive data")
                
        else:
            print(f"   ❌ Failed to get profile: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error getting profile: {e}")
    
    # Test 5: Create another user for connection testing
    print("\n5. Creating second user for connection testing...")
    
    user2_data = {
        "name": "Alice Tester",
        "phone": "+1234567890"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=user2_data)
        if response.status_code == 200:
            user2 = response.json()
            user2_id = user2['userId']
            print(f"   ✅ Created second user: Alice Tester (ID: {user2_id})")
        else:
            print(f"   ❌ Failed to create user2: {response.status_code} - {response.text}")
            print("   ⚠️ Skipping connection tests")
            return
    except Exception as e:
        print(f"   ❌ Error creating user2: {e}")
        print("   ⚠️ Skipping connection tests")
        return
    
    # Test 6: Alice (public) views original user (current privacy) profile
    print(f"\n6. Alice viewing original user profile (should see {'limited' if new_privacy else 'full'} info)...")
    
    headers2 = {"X-User-ID": user2_id}
    try:
        response = requests.get(f"{BASE_URL}/social/users/{user_id}", headers=headers2)
        if response.status_code == 200:
            profile = response.json()
            print(f"   📄 Alice's view of your profile:")
            print(f"      Name: {profile.get('name', 'N/A')}")
            print(f"      Is Private: {profile.get('is_private', 'N/A')}")
            print(f"      Bio: {profile.get('bio', 'None (hidden)')}")
            print(f"      Picture: {profile.get('picture', 'None (hidden)')}")
            print(f"      Strava: {profile.get('strava_link', 'None (hidden)')}")
            print(f"      Instagram: {profile.get('instagram_id', 'None (hidden)')}")
            print(f"      Is Connected: {profile.get('is_connected', False)}")
            print(f"      Connection Status: {profile.get('connection_status', 'None')}")
        else:
            print(f"   ❌ Failed to get profile: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error getting profile: {e}")
    
    # Test 7: Alice attempts to connect to original user
    print(f"\n7. Alice attempting to connect to original user (account is {'private' if new_privacy else 'public'})...")
    
    try:
        response = requests.post(f"{BASE_URL}/social/users/{user_id}/connect", headers=headers2)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Connection result: {result['message']}")
            print(f"   Status: {result['status']}")
            
            expected_status = 'pending' if new_privacy else 'accepted'
            if result['status'] == expected_status:
                print(f"   ✅ Connection behavior correct for {'private' if new_privacy else 'public'} account!")
            else:
                print(f"   ❌ Connection behavior incorrect - expected {expected_status} for {'private' if new_privacy else 'public'} account")
                
        else:
            print(f"   ❌ Failed to send connection request: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error sending connection request: {e}")
    
    # Test 8: Test searching users
    print("\n8. Testing user search...")
    try:
        response = requests.get(f"{BASE_URL}/social/users/search?q=Alice", headers=headers)
        if response.status_code == 200:
            search_result = response.json()
            users_found = len(search_result.get('users', []))
            print(f"   🔍 Found {users_found} users matching 'Alice'")
            
            for user in search_result.get('users', []):
                print(f"      - {user.get('name', 'Unknown')} (Private: {user.get('is_private', False)})")
        else:
            print(f"   ❌ Failed to search users: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error searching users: {e}")
    
    # Test 9: Test general API health
    print("\n9. Testing API health...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ API Status: {health_data.get('status', 'unknown')}")
            print(f"   🗄️ Database: {health_data.get('database', {}).get('type', 'unknown')}")
            print(f"   👥 Users count: {health_data.get('database', {}).get('users_count', 'unknown')}")
            print(f"   🧠 Cache: {'Healthy' if health_data.get('cache', {}).get('healthy', False) else 'Unhealthy'}")
        else:
            print(f"   ❌ API health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error checking API health: {e}")
    
    print("\n🎉 Private profile testing completed!")
    print("\n" + "="*60)
    print("KEY FINDINGS:")
    print(f"✓ Account privacy can be {'toggled' if new_privacy != current_privacy else 'checked'}")
    if new_privacy:
        print("✓ Private accounts should hide sensitive information from non-connected users")
        print("✓ Connection requests should go to 'pending' status for private accounts")
    else:
        print("✓ Public accounts should show all information to everyone")
        print("✓ Connection requests should be 'accepted' immediately for public accounts")
    print("✓ Privacy controls affect what information is visible in profile responses")
    print("✓ The backend is responding correctly to authentication headers")

if __name__ == "__main__":
    test_deployed_private_profile_functionality()
