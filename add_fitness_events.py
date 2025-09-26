#!/usr/bin/env python3
"""
Script to add 50 new fitness-oriented events to the Railway instance.
Creates 40 free events and 10 paid events with fitness themes.
"""

import requests
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import random

# Fitness-oriented event templates
FREE_EVENT_TEMPLATES = [
    "Monday Free Run",
    "Tuesday Yoga Session",
    "Wednesday Free Run",
    "Thursday HIIT Class",
    "Friday Free Run",
    "Saturday Long Run",
    "Sunday Recovery Run",
    "BHAG Free Run",
    "Morning Cardio Blast",
    "Evening Fitness Walk",
    "BHAG Community Run",
    "Free Bodyweight Workout",
    "Open Gym Session",
    "BHAG Group Fitness",
    "Free Stretching Class",
    "BHAG Morning Run",
    "Free Cardio Dance",
    "BHAG Evening Run",
    "Free Strength Training",
    "BHAG Weekend Run",
    "Free Pilates Session",
    "BHAG Sunrise Run",
    "Free CrossFit Intro",
    "BHAG Sunset Run",
    "Free Meditation Walk",
    "BHAG Trail Run",
    "Free Zumba Class",
    "BHAG Park Run",
    "Free Bootcamp",
    "BHAG City Run",
    "Free Yoga Flow",
    "BHAG River Run",
    "Free Circuit Training",
    "BHAG Hill Run",
    "Free Dance Fitness",
    "BHAG Beach Run",
    "Free Core Workout",
    "BHAG Forest Run",
    "Free Flexibility Class",
    "BHAG Lake Run"
]

PAID_EVENT_TEMPLATES = [
    "BHAG 5K Marathon",
    "BHAG 10K Challenge",
    "BHAG Half Marathon",
    "BHAG 25K Marathon",
    "BHAG Ultra Marathon",
    "Premium Yoga Workshop",
    "Advanced HIIT Training",
    "BHAG Marathon Training",
    "Professional Running Clinic",
    "Elite Fitness Camp"
]

# Fitness-oriented banner URLs
FITNESS_BANNER_URLS = [
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1517963628607-235ccdd5476c?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1517963628607-235ccdd5476c?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1581009137042-c552e485697a?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1517963628607-235ccdd5476c?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1517963628607-235ccdd5476c?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1581009137042-c552e485697a?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?w=800&h=400&fit=crop"
]

# Cities and venues with real coordinates
CITIES_COORDINATES = {
    "Mumbai": {"lat": "19.0760", "long": "72.8777"},
    "Delhi": {"lat": "28.7041", "long": "77.1025"},
    "Bangalore": {"lat": "12.9716", "long": "77.5946"},
    "Pune": {"lat": "18.5204", "long": "73.8567"},
    "Chennai": {"lat": "13.0827", "long": "80.2707"},
    "Hyderabad": {"lat": "17.3850", "long": "78.4867"},
    "Kolkata": {"lat": "22.5726", "long": "88.3639"},
    "Ahmedabad": {"lat": "23.0225", "long": "72.5714"}
}

CITIES = list(CITIES_COORDINATES.keys())
VENUES = [
    "Central Park",
    "Marine Drive",
    "India Gate Grounds",
    "Cubbon Park",
    "Phoenix Mall Grounds",
    "Nehru Stadium",
    "City Sports Complex",
    "Riverside Park",
    "Fitness Hub Arena",
    "Community Center Grounds"
]

def generate_datetime(days_ahead: int = 0) -> tuple[str, str]:
    """Generate start and end datetime strings for events."""
    # Use UTC time to avoid timezone issues
    now = datetime.now()
    start_time = now + timedelta(days=days_ahead, hours=random.randint(6, 10))
    end_time = start_time + timedelta(hours=random.randint(2, 4))

    # Format as ISO string with timezone info to match backend expectations
    start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')  # IST timezone
    end_iso = end_time.strftime('%Y-%m-%dT%H:%M:%S+05:30')      # IST timezone

    return start_iso, end_iso

def generate_event_description(title: str) -> str:
    """Generate fitness-oriented description for an event."""
    descriptions = [
        f"Join us for an invigorating {title.lower()} session. Perfect for all fitness levels!",
        f"Experience the energy of {title.lower()} with fellow fitness enthusiasts. Let's get moving!",
        f"Start your day right with {title.lower()}. A great way to stay fit and healthy!",
        f"Community fitness at its best! Join {title.lower()} and connect with like-minded people.",
        f"Free fitness fun! Come participate in {title.lower()} and boost your energy levels.",
        f"Get your heart pumping with {title.lower()}. Open to everyone who loves staying active!",
        f"Transform your routine with {title.lower()}. Fitness, fun, and community spirit!",
        f"Stay motivated and active with {title.lower()}. Your fitness journey starts here!"
    ]
    return random.choice(descriptions)

def create_fitness_events(railway_url: str) -> Dict[str, Any]:
    """
    Create 50 fitness-oriented events (40 free, 10 paid).

    Args:
        railway_url: The Railway app URL (e.g., https://your-app.railway.app)

    Returns:
        Dict containing results of the operation
    """
    base_url = railway_url.rstrip('/')

    print(f"🏃 Starting to create 50 fitness events at: {base_url}")
    print("=" * 60)

    results = {
        "total_events": 50,
        "free_events": 40,
        "paid_events": 10,
        "successful_creations": 0,
        "failed_creations": 0,
        "errors": []
    }

    try:
        # Generate 40 free events
        free_events = []
        for i in range(40):
            title = FREE_EVENT_TEMPLATES[i % len(FREE_EVENT_TEMPLATES)]
            city = random.choice(CITIES)
            venue = random.choice(VENUES)
            start_at, end_at = generate_datetime(days_ahead=random.randint(1, 30))
            banner_url = random.choice(FITNESS_BANNER_URLS)
            description = generate_event_description(title)

            event_data = {
                "title": f"{title} #{i+1:03d}",
                "description": description,
                "city": city,
                "venue": venue,
                "startAt": start_at,
                "endAt": end_at,
                "priceINR": 0,  # Free event
                "bannerUrl": banner_url,
                "isActive": True,
                "organizerName": "BHAG Fitness Club",
                "organizerLogo": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=200&h=200&fit=crop",
                "coordinate_lat": CITIES_COORDINATES[city]["lat"],
                "coordinate_long": CITIES_COORDINATES[city]["long"],
                "address_url": f"https://maps.google.com/?q={venue.replace(' ', '+')}+{city.replace(' ', '+')}"
            }
            free_events.append(event_data)

        # Generate 10 paid events
        paid_events = []
        for i in range(10):
            title = PAID_EVENT_TEMPLATES[i % len(PAID_EVENT_TEMPLATES)]
            city = random.choice(CITIES)
            venue = random.choice(VENUES)
            start_at, end_at = generate_datetime(days_ahead=random.randint(7, 60))  # Further in future
            banner_url = random.choice(FITNESS_BANNER_URLS)
            description = generate_event_description(title)
            price = random.randint(100, 1000)  # Random price between ₹100-1000

            event_data = {
                "title": f"{title} #{i+1:03d}",
                "description": description,
                "city": city,
                "venue": venue,
                "startAt": start_at,
                "endAt": end_at,
                "priceINR": price,  # Paid event
                "bannerUrl": banner_url,
                "isActive": True,
                "organizerName": "BHAG Elite Fitness",
                "organizerLogo": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=200&h=200&fit=crop",
                "coordinate_lat": CITIES_COORDINATES[city]["lat"],
                "coordinate_long": CITIES_COORDINATES[city]["long"],
                "address_url": f"https://maps.google.com/?q={venue.replace(' ', '+')}+{city.replace(' ', '+')}"
            }
            paid_events.append(event_data)

        # Combine all events
        all_events = free_events + paid_events
        random.shuffle(all_events)  # Randomize order

        print(f"📋 Created {len(all_events)} events to add:")
        print(f"   • Free events: {len(free_events)}")
        print(f"   • Paid events: {len(paid_events)}")
        print()

        # Create events one by one
        for i, event_data in enumerate(all_events):
            event_title = event_data["title"]
            event_price = event_data["priceINR"]
            event_type = "FREE" if event_price == 0 else f"PAID (₹{event_price})"

            print(f"🏃 Creating event {i+1}/{len(all_events)}: {event_title} ({event_type})")
            print(f"   📅 Start: {event_data['startAt']}, End: {event_data['endAt']}")
            print(f"   📍 Location: {event_data['city']} - {event_data['venue']}")

            try:
                response = requests.post(
                    f"{base_url}/events",
                    json=event_data,
                    timeout=30
                )

                if response.status_code == 200:
                    response_data = response.json()
                    # Handle case where backend returns a list instead of single event
                    if isinstance(response_data, list):
                        # If it's a list, take the last item (newly created event)
                        created_event = response_data[-1] if response_data else None
                        print(f"✅ Successfully created: {event_title} (List response - {len(response_data)} events)")
                    else:
                        # If it's a single event object
                        created_event = response_data
                        print(f"✅ Successfully created: {event_title} (ID: {created_event.get('id', 'N/A')})")

                    results["successful_creations"] += 1
                else:
                    error_msg = f"Failed to create '{event_title}'. Status: {response.status_code}, Response: {response.text}"
                    print(f"❌ {error_msg}")
                    results["errors"].append(error_msg)
                    results["failed_creations"] += 1

            except requests.exceptions.RequestException as e:
                error_msg = f"Network error creating '{event_title}': {str(e)}"
                print(f"❌ {error_msg}")
                results["errors"].append(error_msg)
                results["failed_creations"] += 1

            # Add delay to avoid overwhelming the server
            if i < len(all_events) - 1:
                time.sleep(0.5)

        # Comprehensive debugging after creation
        print("\n🔍 Comprehensive debugging...")

        # Check 1: Raw events from database
        print("📋 Check 1: Testing direct database access...")
        try:
            # Try to access events through different endpoints
            endpoints_to_check = [
                "/events",
                "/events/recent",
                "/events/recent?limit=50"
            ]

            for endpoint in endpoints_to_check:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=30)
                    if response.status_code == 200:
                        events = response.json()
                        print(f"   ✅ {endpoint}: Found {len(events)} events")
                        if events and len(events) <= 5:  # Show details if not too many
                            for event in events:
                                print(f"      • {event.get('title', 'Unknown')} - {event.get('city', 'Unknown')}")
                                print(f"        Active: {event.get('isActive', 'Unknown')}, End: {event.get('endAt', 'Unknown')}")
                        elif events:
                            print(f"      • First event: {events[0].get('title', 'Unknown')}")
                            print(f"      • Last event: {events[-1].get('title', 'Unknown')}")
                    else:
                        print(f"   ❌ {endpoint}: Status {response.status_code}")
                except Exception as e:
                    print(f"   ❌ {endpoint}: Error {str(e)}")
        except Exception as e:
            print(f"❌ Error in debugging: {str(e)}")

        # Check 2: Test with a very future event
        print("\n🏃 Check 2: Creating a test event far in the future...")
        future_event = {
            "title": "FUTURE TEST EVENT - FAR FUTURE",
            "description": "This event is scheduled far in the future to test visibility",
            "city": "Mumbai",
            "venue": "Test Venue Far Future",
            "startAt": "2025-12-01T10:00:00",
            "endAt": "2025-12-01T14:00:00",
            "priceINR": 0,
            "bannerUrl": "https://via.placeholder.com/800x400",
            "isActive": True,
            "organizerName": "Future Test Organizer",
            "organizerLogo": "https://via.placeholder.com/200x200",
            "coordinate_lat": "19.0760",
            "coordinate_long": "72.8777",
            "address_url": "https://maps.google.com/?q=Test+Venue+Far+Future+Mumbai"
        }

        try:
            response = requests.post(f"{base_url}/events", json=future_event, timeout=30)
            if response.status_code == 200:
                print("   ✅ Future test event created successfully")
                # Check if this future event is visible
                time.sleep(2)  # Wait a moment for processing
                check_response = requests.get(f"{base_url}/events", timeout=30)
                if check_response.status_code == 200:
                    future_events = check_response.json()
                    print(f"   📊 After future event creation: Found {len(future_events)} events")
                    if future_events:
                        future_test_found = any("FUTURE TEST EVENT" in e.get('title', '') for e in future_events)
                        print(f"   🎯 Future test event visible: {future_test_found}")
                else:
                    print(f"   ❌ Failed to check events after future event: {check_response.status_code}")
            else:
                print(f"   ❌ Failed to create future test event: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error with future test event: {str(e)}")

        print("=" * 60)
        print("📈 Creation Summary:")
        print(f"   • Total events attempted: {len(all_events)}")
        print(f"   • Successfully created: {results['successful_creations']}")
        print(f"   • Failed to create: {results['failed_creations']}")
        print(f"   • Free events: {len(free_events)}")
        print(f"   • Paid events: {len(paid_events)}")

        if results["errors"]:
            print(f"   • Errors encountered: {len(results['errors'])}")
            print("\n❌ Errors:")
            for error in results["errors"][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(results["errors"]) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")

        if results["successful_creations"] == len(all_events):
            print("🎉 All 50 fitness events have been successfully created!")
        else:
            print(f"⚠️  Created {results['successful_creations']}/{len(all_events)} events. Check errors above.")

        return results

    except Exception as e:
        error_msg = f"Unexpected error occurred: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results

def main():
    """Main function to run the script."""
    if len(sys.argv) != 2:
        print("Usage: python add_fitness_events.py <RAILWAY_URL>")
        print("Example: python add_fitness_events.py https://your-app.railway.app")
        sys.exit(1)

    railway_url = sys.argv[1]

    if not railway_url.startswith(('http://', 'https://')):
        print("❌ Please provide a valid URL starting with http:// or https://")
        sys.exit(1)

    # Run the event creation process
    results = create_fitness_events(railway_url)

    # Exit with appropriate code
    if results["errors"]:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
