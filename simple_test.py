#!/usr/bin/env python3
"""
Simple test to create one event and check if it's visible.
"""

import requests
import json
import sys
from datetime import datetime, timedelta

def simple_test(railway_url: str):
    """Create one event and check if it's visible."""
    base_url = railway_url.rstrip('/')

    print(f"🔬 Simple test at: {base_url}")
    print("=" * 40)

    # Test 1: Check current events
    print("📋 Before: Checking current events...")
    try:
        response = requests.get(f"{base_url}/events", timeout=30)
        before_count = 0
        if response.status_code == 200:
            events = response.json()
            before_count = len(events)
            print(f"   ✅ Found {before_count} events")
        else:
            print(f"   ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

    # Test 2: Create one simple event
    print("\n🏃 Creating one simple test event...")
    test_event = {
        "title": "SIMPLE TEST EVENT",
        "description": "Simple test event",
        "city": "Mumbai",
        "venue": "Test Venue",
        "startAt": "2025-10-01T10:00:00",
        "endAt": "2025-10-01T12:00:00",
        "priceINR": 0,
        "bannerUrl": "https://via.placeholder.com/800x400",
        "isActive": True,
        "organizerName": "Test",
        "organizerLogo": "https://via.placeholder.com/200x200",
        "coordinate_lat": "19.0760",
        "coordinate_long": "72.8777",
        "address_url": "https://maps.google.com/?q=Test+Venue+Mumbai"
    }

    try:
        response = requests.post(f"{base_url}/events", json=test_event, timeout=30)
        if response.status_code == 200:
            print("   ✅ Event created successfully"            # Check response type
            response_data = response.json()
            if isinstance(response_data, list):
                print(f"   📋 Response is a list with {len(response_data)} items")
                if response_data:
                    print(f"   📝 Last item: {response_data[-1].get('title', 'Unknown')}")
            else:
                print(f"   📋 Response is a single object: {response_data.get('title', 'Unknown')}")
        else:
            print(f"   ❌ Failed to create: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error creating event: {str(e)}")
        return

    # Test 3: Check events after creation
    print("\n📋 After: Checking events again...")
    try:
        response = requests.get(f"{base_url}/events", timeout=30)
        after_count = 0
        if response.status_code == 200:
            events = response.json()
            after_count = len(events)
            print(f"   ✅ Found {after_count} events (was {before_count})")

            # Check if our test event is there
            test_event_found = any("SIMPLE TEST EVENT" in e.get('title', '') for e in events)
            print(f"   🎯 Test event visible: {test_event_found}")

            if events:
                print("   📝 All events:")
                for i, event in enumerate(events):
                    print(f"      {i+1}. {event.get('title', 'Unknown')} - {event.get('city', 'Unknown')}")
                    print(f"         Active: {event.get('isActive', 'Unknown')}")
                    print(f"         End: {event.get('endAt', 'Unknown')}")
        else:
            print(f"   ❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

    # Test 4: Try different endpoints
    print("\n🔍 Testing different endpoints...")
    endpoints = ["/events", "/events/recent", "/events/recent?limit=100"]

    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=30)
            if response.status_code == 200:
                events = response.json()
                print(f"   ✅ {endpoint}: {len(events)} events")
            else:
                print(f"   ❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {endpoint}: Error {str(e)}")

    print("\n" + "=" * 40)
    print("🔬 Test complete!")

def main():
    if len(sys.argv) != 2:
        print("Usage: python simple_test.py <RAILWAY_URL>")
        print("Example: python simple_test.py https://your-app.railway.app")
        sys.exit(1)

    railway_url = sys.argv[1]
    if not railway_url.startswith(('http://', 'https://')):
        print("❌ Please provide a valid URL starting with http:// or https://")
        sys.exit(1)

    simple_test(railway_url)

if __name__ == "__main__":
    main()
