#!/usr/bin/env python3
"""
Test private account connection request flow to verify if manual acceptance is required.
"""

import requests
import json
import time

BASE_URL = "https://initialbackend-production.up.railway.app"

def test_private_connection_flow():
    """Test connection flow for private accounts"""
    
    print("🔗 Testing Private Account Connection Flow")
    print("=" * 60)
    
    # Existing user (currently private)
    user_id = "u_872e4600ed"
    headers = {"X-User-ID": user_id}
    
    print(f"Using existing user: {user_id}")
    
    # Test 1: Ensure user is currently private
    print("\n1. Checking current privacy setting...")
    try:
        response = requests.get(f"{BASE_URL}/social/users/{user_id}/privacy", headers=headers)
        if response.status_code == 200:
            privacy_data = response.json()
            is_private = privacy_data['is_private']
            print(f"   🔒 Current privacy setting: {'Private' if is_private else 'Public'}")
            
            if not is_private:
                # Toggle to private if currently public
                print("   🔄 Toggling to private...")
                requests.put(f"{BASE_URL}/social/users/{user_id}/privacy", headers=headers)
                is_private = True
        else:
            print(f"   ❌ Failed to get privacy: {response.status_code}")
            is_private = True  # Assume private
    except Exception as e:
        print(f"   ❌ Error checking privacy: {e}")
        is_private = True
    
    # Test 2: Create a second user to test connection flow
    print("\n2. Creating second user for connection testing...")
    
    # Try different phone numbers in case some exist
    test_phones = ["+9999911111", "+8888822222", "+7777733333", "+6666644444"]
    user2_id = None
    
    for phone in test_phones:
        user2_data = {
            "name": f"Alice Tester {phone[-4:]}",
            "phone": phone,
            "email": f"alice{phone[-4:]}@test.com",
            "password": "testpass123"
        }
        
        try:
            # Try registration first
            response = requests.post(f"{BASE_URL}/auth/register", json=user2_data)
            if response.status_code == 200:
                user2 = response.json()
                user2_id = user2['user']['id']
                user2_name = user2['user']['name']
                print(f"   ✅ Created second user: {user2_name} (ID: {user2_id})")
                break
            else:
                print(f"   ⚠️ Phone {phone} already exists, trying next...")
                continue
        except Exception as e:
            print(f"   ❌ Error creating user with phone {phone}: {e}")
            continue
    
    if not user2_id:
        print("   ❌ Could not create second user - all test phones likely exist")
        print("   🔄 Trying alternative approach...")
        
        # Get existing users for testing (if any are found via search)
        try:
            response = requests.get(f"{BASE_URL}/social/users/search?q=test", headers=headers)
            if response.status_code == 200:
                search_users = response.json().get('users', [])
                if search_users:
                    user2 = search_users[0]
                    user2_id = user2['id']
                    print(f"   ✅ Using existing user for testing: {user2.get('name', 'Unknown')} (ID: {user2_id})")
                else:
                    print("   ❌ No existing users found for testing")
                    return
            else:
                print("   ❌ Search failed")
                return
        except Exception as e:
            print(f"   ❌ Error searching users: {e}")
            return
    
    # Test 3: Test connection request from second user to private account
    print(f"\n3. Testing connection request flow...")
    print(f"   User 2 ({user2_id}) → User 1 ({user_id}) [Private Account]")
    
    headers2 = {"X-User-ID": user2_id}
    
    try:
        response = requests.post(f"{BASE_URL}/social/users/{user_id}/connect", headers=headers2)
        if response.status_code == 200:
            connection_result = response.json()
            print(f"   📨 Connection request result:")
            print(f"      Message: {connection_result.get('message', 'N/A')}")
            print(f"      Status: {connection_result.get('status', 'N/A')}")
            print(f"      Success: {connection_result.get('success', 'N/A')}")
            
            expected_status = 'pending'  # Private accounts should require manual acceptance
            actual_status = connection_result.get('status')
            
            if actual_status == expected_status:
                print("   ✅ Connection behavior CORRECT - Private account requires manual acceptance!")
            elif actual_status == 'accepted':
                print("   ❌ Connection behavior INCORRECT - Private account auto-accepted!")
            else:
                print(f"   ⚠️ Unexpected status: {actual_status}")
                
        else:
            print(f"   ❌ Connection request failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error sending connection request: {e}")
    
    # Test 4: Check if pending requests exist for the private account owner
    print(f"\n4. Checking for pending connection requests...")
    
    try:
        response = requests.get(f"{BASE_URL}/social/connection-requests", headers=headers)
        if response.status_code == 200:
            requests_data = response.json()
            pending_count = len(requests_data)
            print(f"   📋 Found {pending_count} pending connection requests")
            
            if pending_count > 0:
                print("   ✅ Pending requests found - Manual acceptance required!")
                
                # Show details of pending requests
                for req in requests_data:
                    print(f"      - Request ID: {req.get('id', 'N/A')}")
                    print(f"        From: {req.get('requester', {}).get('name', 'Unknown')}")
                    print(f"        Created: {req.get('created_at', 'N/A')}")
                    
                    # Test accepting the request
                    request_id = req.get('id')
                    print(f"\n5. Testing manual acceptance of connection request...")
                    
                    try:
                        response = requests.post(f"{BASE_URL}/social/connection-requests/{request_id}/accept", headers=headers)
                        if response.status_code == 200:
                            accept_result = response.json()
                            print(f"   ✅ Request accepted: {accept_result.get('message', 'N/A')}")
                            
                            # Test profile view after acceptance
                            print(f"\n6. Testing profile visibility after connection accepted...")
                            
                            # User 2 viewing User 1's profile after connection
                            try:
                                response = requests.get(f"{BASE_URL}/social/users/{user_id}", headers=headers2)
                                if response.status_code == 200:
                                    profile_after = response.json()
                                    print(f"   📄 Profile view after connection:")
                                    print(f"      Name: {profile_after.get('name', 'N/A')}")
                                    print(f"      Is Private: {profile_after.get('is_private', 'N/A')}")
                                    print(f"      Is Connected: {profile_after.get('is_connected', False)}")
                                    print(f"      Connection Status: {profile_after.get('connection_status', 'N/A')}")
                                    print(f"      Bio: {profile_after.get('bio', 'None')}")
                                    print(f"      Picture: {profile_after.get('picture', 'None')}")
                                    print(f"      Strava: {profile_after.get('strava_link', 'None')}")
                                    print(f"      Instagram: {profile_after.get('instagram_id', 'None')}")
                                    
                                    if profile_after.get('is_connected') == True:
                                        print("   ✅ Connection properly established!")
                                    else:
                                        print("   ❌ Connection not properly established")
                                        
                                else:
                                    print(f"   ❌ Failed to get profile after acceptance: {response.status_code}")
                                    
                            except Exception as e:
                                print(f"   ❌ Error testing profile after acceptance: {e}")
                            
                        else:
                            print(f"   ❌ Failed to accept request: {response.status_code} - {response.text}")
                            
                    except Exception as e:
                        print(f"   ❌ Error accepting request: {e}")
                        
            else:
                print("   ⚠️ No pending requests found")
                
        else:
            print(f"   ❌ Failed to get connection requests: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error checking connection requests: {e}")
    
    # Test 6: Test public account behavior for comparison
    print(f"\n7. Testing public account behavior for comparison...")
    
    # Toggle user to public
    try:
        response = requests.put(f"{BASE_URL}/social/users/{user_id}/privacy", headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"   🔄 Toggled to: {result['message']}")
            
            # Try connection again
            try:
                response = requests.post(f"{BASE_URL}/social/users/{user_id}/connect", headers=headers2)
                if response.status_code == 200:
                    public_result = response.json()
                    print(f"   📨 Public account connection result:")
                    print(f"      Status: {public_result.get('status', 'N/A')}")
                    print(f"      Message: {public_result.get('message', 'N/A')}")
                    
                    if public_result.get('status') == 'accepted':
                        print("   ✅ Public account behavior CORRECT - Auto-accepted!")
                    else:
                        print("   ❌ Public account behavior INCORRECT - Should auto-accept!")
                        
                else:
                    print(f"   ❌ Public connection failed: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error testing public connection: {e}")
                
        else:
            print(f"   ❌ Failed to toggle to public: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing public behavior: {e}")
    
    print("\n🎉 Connection flow testing completed!")
    print("\n" + "="*60)
    print("EXPECTED BEHAVIOR:")
    print("✅ Private accounts: Connection requests → PENDING → Manual acceptance required")
    print("✅ Public accounts: Connection requests → AUTO-ACCEPTED")
    print("✅ After acceptance: Connected users can see full profile")
    print("✅ Privacy controls: Hide sensitive data until connected")

if __name__ == "__main__":
    test_private_connection_flow()
