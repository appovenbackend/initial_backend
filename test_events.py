#!/usr/bin/env python3
"""
Simple test script to debug event creation issues.
"""

import requests
import json
import sys
from datetime import datetime, timedelta

def test_events(railway_url: str):
    """Test event creation and retrieval."""
    base_url = railway_url.rstrip('/')

    print(f"🔍 Testing events at: {base_url}")
    print("=" * 50)

    # Test 1: Check current events
    print("📋 Test 1: Checking current events...")
    try:
        response = requests.get(f"{base_url}/events", timeout=30)
        if response.status_code == 200:
            events = response.json()
            print(f"   ✅ Found {len(events)} events")
            if events:
                print("   📝 Sample events:")
                for event in events[:3]:
                    print(f"      • {event.get('title', 'Unknown')} - {event.get('city', 'Unknown')}")
            else:
                print("   ⚠️  No events found")
        else:
            print(f"   ❌ Failed to get events: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

    # Test 2: Create a simple test event
    print("\n🏃 Test 2: Creating a simple test event...")
    test_event = {
        "title": "TEST EVENT - DELETE ME",
        "description": "This is a test event to debug creation issues",
        "city": "Mumbai",
        "venue": "Test Venue",
        "startAt": "2024-12-31T10:00:00",
        "endAt": "2024-12-31T12:00:00",
        "priceINR": 0,
        "bannerUrl": "https://via.placeholder.com/800x400",
        "isActive": True,
        "organizerName": "Test Organizer",
        "organizerLogo": "https://via.placeholder.com/200x200",
        "coordinate_lat": "19.0760",
        "coordinate_long": "72.8777",
        "address_url": "https://maps.google.com/?q=Test+Venue+Mumbai"
    }

    try:
        response = requests.post(f"{base_url}/events", json=test_event, timeout=30)
        if response.status_code == 200:
            response_data = response.json()
            # Handle case where backend returns a list instead of single event
            if isinstance(response_data, list):
                # If it's a list, take the last item (newly created event)
                created_event = response_data[-1] if response_data else None
                print(f"   ✅ Successfully created test event! (List response - {len(response_data)} events)")
            else:
                # If it's a single event object
                created_event = response_data
                print(f"   ✅ Successfully created test event!")
                print(f"   🆔 Event ID: {created_event.get('id', 'N/A')}")
                print(f"   📅 Created At: {created_event.get('createdAt', 'N/A')}")
        else:
            print(f"   ❌ Failed to create test event: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error creating test event: {str(e)}")

    # Test 3: Check events again
    print("\n📋 Test 3: Checking events after test creation...")
    try:
        response = requests.get(f"{base_url}/events", timeout=30)
        if response.status_code == 200:
            events = response.json()
            print(f"   ✅ Found {len(events)} events")
            if events:
                print("   📝 Recent events:")
                for event in events[-3:]:  # Show last 3 (most recent)
                    print(f"      • {event.get('title', 'Unknown')} - {event.get('city', 'Unknown')}")
                    print(f"        Created: {event.get('createdAt', 'Unknown')}")
            else:
                print("   ⚠️  Still no events found")
        else:
            print(f"   ❌ Failed to get events: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

    # Test 4: Check health endpoint
    print("\n🏥 Test 4: Checking backend health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=30)
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ Backend is healthy")
            print(f"   🗄️  Database: {health.get('database', {}).get('type', 'Unknown')}")
            print(f"   👥 Users count: {health.get('database', {}).get('users_count', 'Unknown')}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error checking health: {str(e)}")

    print("\n" + "=" * 50)
    print("🔍 Debug complete!")

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_events.py <RAILWAY_URL>")
        print("Example: python test_events.py https://your-app.railway.app")
        sys.exit(1)

    railway_url = sys.argv[1]
    if not railway_url.startswith(('http://', 'https://')):
        print("❌ Please provide a valid URL starting with http:// or https://")
        sys.exit(1)

    test_events(railway_url)

if __name__ == "__main__":
    main()
