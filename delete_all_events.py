#!/usr/bin/env python3
"""
Script to delete all existing events in the Railway instance.
This script deactivates all events by setting isActive to false.
"""

import requests
import json
import sys
import time
from typing import List, Dict, Any

def delete_all_events(railway_url: str) -> Dict[str, Any]:
    """
    Delete all events by deactivating them.

    Args:
        railway_url: The Railway app URL (e.g., https://your-app.railway.app)

    Returns:
        Dict containing results of the operation
    """
    # Ensure URL doesn't end with trailing slash
    base_url = railway_url.rstrip('/')

    print(f"🔄 Starting to delete all events from: {base_url}")
    print("=" * 50)

    results = {
        "total_events": 0,
        "deactivated_events": 0,
        "failed_events": 0,
        "errors": []
    }

    try:
        # Step 1: Get all events
        print("📋 Fetching all events...")
        events_response = requests.get(f"{base_url}/events", timeout=30)

        if events_response.status_code != 200:
            error_msg = f"Failed to fetch events. Status: {events_response.status_code}, Response: {events_response.text}"
            print(f"❌ {error_msg}")
            results["errors"].append(error_msg)
            return results

        events = events_response.json()
        results["total_events"] = len(events)

        if not events:
            print("✅ No events found. Nothing to delete.")
            return results

        print(f"📊 Found {len(events)} events to process")

        # Step 2: Deactivate each event
        for i, event in enumerate(events):
            event_id = event.get("id")
            event_title = event.get("title", "Unknown Event")

            print(f"🔄 Processing event {i+1}/{len(events)}: {event_title} (ID: {event_id})")

            # Deactivate the event using PATCH endpoint
            patch_data = {"isActive": False}
            patch_response = requests.patch(
                f"{base_url}/events/{event_id}",
                json=patch_data,
                timeout=30
            )

            if patch_response.status_code == 200:
                print(f"✅ Successfully deactivated: {event_title}")
                results["deactivated_events"] += 1
            else:
                error_msg = f"Failed to deactivate event '{event_title}' (ID: {event_id}). Status: {patch_response.status_code}, Response: {patch_response.text}"
                print(f"❌ {error_msg}")
                results["errors"].append(error_msg)
                results["failed_events"] += 1

            # Add a small delay to avoid overwhelming the server
            if i < len(events) - 1:  # Don't delay after the last event
                time.sleep(0.5)

        print("=" * 50)
        print("📈 Operation Summary:")
        print(f"   • Total events found: {results['total_events']}")
        print(f"   • Successfully deactivated: {results['deactivated_events']}")
        print(f"   • Failed to deactivate: {results['failed_events']}")

        if results["errors"]:
            print(f"   • Errors encountered: {len(results['errors'])}")
            print("\n❌ Errors:")
            for error in results["errors"]:
                print(f"   - {error}")

        if results["deactivated_events"] == results["total_events"]:
            print("🎉 All events have been successfully deactivated!")
        else:
            print("⚠️  Some events could not be deactivated. Check the errors above.")

        return results

    except requests.exceptions.RequestException as e:
        error_msg = f"Network error occurred: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse JSON response: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results
    except Exception as e:
        error_msg = f"Unexpected error occurred: {str(e)}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results

def main():
    """Main function to run the script."""
    if len(sys.argv) != 2:
        print("Usage: python delete_all_events.py <RAILWAY_URL>")
        print("Example: python delete_all_events.py https://your-app.railway.app")
        sys.exit(1)

    railway_url = sys.argv[1]

    if not railway_url.startswith(('http://', 'https://')):
        print("❌ Please provide a valid URL starting with http:// or https://")
        sys.exit(1)

    # Run the deletion process
    results = delete_all_events(railway_url)

    # Exit with appropriate code
    if results["errors"]:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
