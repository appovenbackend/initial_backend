#!/usr/bin/env python3
"""
Test script for featured events functionality.
This script demonstrates how the featured events endpoints work.
"""

import requests
import json

# Local development server
BASE_URL = "http://localhost:8000"

def test_featured_events():
    """Test the featured events functionality."""

    print("🧪 Testing Featured Events Functionality")
    print("=====================================")

    # Test 1: Check if events exist
    print("\n1. Checking existing events...")
    try:
        response = requests.get(f"{BASE_URL}/events/")
        if response.status_code == 200:
            events = response.json()
            print(f"   ✅ Found {len(events)} events")

            if len(events) < 2:
                print("   ⚠️  Need at least 2 events to test featured functionality")
                print("   Create some events first, then run this test again.")
                return
        else:
            print(f"   ❌ Failed to get events: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # Test 2: Get current featured events
    print("\n2. Getting current featured events...")
    try:
        response = requests.get(f"{BASE_URL}/events/featured")
        if response.status_code == 200:
            featured = response.json()
            print(f"   ✅ Found {len(featured)} featured events")
        else:
            print(f"   ❌ Failed to get featured events: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Set featured events
    print("\n3. Setting featured events...")
    try:
        event_ids = [events[0]['id'], events[1]['id']]
        response = requests.post(f"{BASE_URL}/events/featured", json=event_ids)

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Successfully set {len(result['featured_events'])} events as featured")
            print(f"   📋 Featured event IDs: {result['featured_event_ids']}")
        else:
            print(f"   ❌ Failed to set featured events: {response.status_code}")
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 4: Get featured events after setting
    print("\n4. Getting featured events after setting...")
    try:
        response = requests.get(f"{BASE_URL}/events/featured")
        if response.status_code == 200:
            featured = response.json()
            print(f"   ✅ Found {len(featured)} featured events:")
            for event in featured:
                print(f"      - {event['title']} (ID: {event['id']})")
        else:
            print(f"   ❌ Failed to get featured events: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 5: Toggle single event
    print("\n5. Toggling single event featured status...")
    try:
        event_id = events[0]['id']
        response = requests.post(f"{BASE_URL}/events/featured/{event_id}")

        if response.status_code == 200:
            result = response.json()
            status = "featured" if result['currently_featured'] else "not featured"
            print(f"   ✅ Event {event_id} is now {status}")
        else:
            print(f"   ❌ Failed to toggle event: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("\n🎉 Featured events test completed!")

if __name__ == "__main__":
    test_featured_events()
