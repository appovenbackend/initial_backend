#!/usr/bin/env python3
"""
Test script to verify private profile privacy controls are working correctly.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_private_profile_functionality():
    """Test private profile privacy controls"""
    
    print("🔒 Testing Private Profile Functionality")
    print("=" * 50)
    
    # Test 1: Create two users - one public, one private
    print("\n1. Creating test users...")
    
    # User 1 (Public)
    user1_data = {
        "name": "Alice Public",
        "phone": "+1111111111"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=user1_data)
        if response.status_code == 200:
            user1 = response.json()
            print(f"   ✅ Created public user: Alice Public (ID: {user1['userId']})")
        else:
            print(f"   ❌ Failed to create user1: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Error creating user1: {e}")
        return
    
    # User 2 (Private) 
    user2_data = {
        "name": "Bob Private", 
        "phone": "+2222222222"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=user2_data)
        if response.status_code == 200:
            user2 = response.json()
            print(f"   ✅ Created private user: Bob Private (ID: {user2['userId']})")
        else:
            print(f"   ❌ Failed to create user2: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Error creating user2: {e}")
        return
    
    # Test 2: Set Bob as private
    print("\n2. Setting Bob's account to private...")
    
    headers = {"X-User-ID": user2["userId"]}
    try:
        response = requests.put(
            f"{BASE_URL}/social/users/{user2['userId']}/privacy",
            json=True,
            headers=headers
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Bob's account set to: {'private' if result['is_private'] else 'public'}")
        else:
            print(f"   ❌ Failed to update privacy: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error updating privacy: {e}")
    
    # Test 3: Alice views Bob's profile (should see limited info)
    print("\n3. Alice viewing Bob's private profile...")
    
    headers = {"X-User-ID": user1["userId"]}
    try:
        response = requests.get(
            f"{BASE_URL}/social/users/{user2['userId']}",
            headers=headers
        )
        if response.status_code == 200:
            profile = response.json()
            print(f"   📄 Profile response:")
            print(f"      Name: {profile['name']}")
            print(f"      Is Private: {profile['is_private']}")
            print(f"      Bio: {profile.get('bio', 'None (hidden)')}")
            print(f"      Picture: {profile.get('picture', 'None (hidden)')}")
            print(f"      Strava: {profile.get('strava_link', 'None (hidden)')}")
            print(f"      Instagram: {profile.get('instagram_id', 'None (hidden)')}")
            
            if profile.get('bio') is None and profile.get('is_private'):
                print("   ✅ Privacy controls working - sensitive info hidden!")
            else:
                print("   ❌ Privacy controls NOT working - sensitive info exposed!")
                
        else:
            print(f"   ❌ Failed to get profile: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting profile: {e}")
    
    # Test 4: Alice sends connection request to Bob
    print("\n4. Alice sending connection request to Bob...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/social/users/{user2['userId']}/connect",
            headers=headers
        )
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Result: {result['message']}")
            print(f"   Status: {result['status']}")
            
            if result['status'] == 'pending':
                print("   ✅ Connection request sent (not auto-accepted for private account)")
            elif result['status'] == 'accepted':
                print("   ❌ Connection auto-accepted (should be pending for private account)")
                
        else:
            print(f"   ❌ Failed to send connection request: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error sending connection request: {e}")
    
    # Test 5: Bob accepts the connection
    print("\n5. Bob accepting Alice's connection request...")
    
    # First get connection requests
    headers = {"X-User-ID": user2["userId"]}
    try:
        response = requests.get(f"{BASE_URL}/social/connection-requests", headers=headers)
        if response.status_code == 200:
            requests_data = response.json()
            print(f"   📋 Found {len(requests_data)} connection requests")
            
            if requests_data:
                request_id = requests_data[0]["id"]
                print(f"   🔗 Accepting request: {request_id}")
                
                # Accept the request
                response = requests.post(
                    f"{BASE_URL}/social/connection-requests/{request_id}/accept",
                    headers=headers
                )
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ {result['message']}")
                else:
                    print(f"   ❌ Failed to accept request: {response.status_code}")
            else:
                print("   ❌ No connection requests found")
                
        else:
            print(f"   ❌ Failed to get connection requests: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error processing connection acceptance: {e}")
    
    # Test 6: Alice views Bob's profile again (should now see full profile)
    print("\n6. Alice viewing Bob's profile after connection accepted...")
    
    headers = {"X-User-ID": user1["userId"]}
    try:
        response = requests.get(
            f"{BASE_URL}/social/users/{user2['userId']}",
            headers=headers
        )
        if response.status_code == 200:
            profile = response.json()
            print(f"   📄 Profile response after connection:")
            print(f"      Name: {profile['name']}")
            print(f"      Is Private: {profile['is_private']}")
            print(f"      Is Connected: {profile.get('is_connected', False)}")
            print(f"      Bio: {profile.get('bio', 'None (hidden)')}")
            print(f"      Picture: {profile.get('picture', 'None (hidden)')}")
            print(f"      Strava: {profile.get('strava_link', 'None (hidden)')}")
            print(f"      Instagram: {profile.get('instagram_id', 'None (hidden)')}")
            
            if profile.get('is_connected') and profile.get('bio') is not None:
                print("   ✅ Connection working - full profile visible after acceptance!")
            elif profile.get('is_connected') and profile.get('bio') is None:
                print("   ❌ Connected but profile still private - check privacy logic!")
            else:
                print("   ❌ Connection not properly established")
                
        else:
            print(f"   ❌ Failed to get profile: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting profile: {e}")
    
    print("\n🎉 Private profile test completed!")
    print("\n" + "="*50)
    print("SUMMARY:")
    print("1. Private accounts should hide bio, picture, links until connected")
    print("2. Connection requests should be pending, not auto-accepted")
    print("3. After connection acceptance, full profile should be visible")
    print("4. Public accounts should always show full profile")

if __name__ == "__main__":
    test_private_profile_functionality()
