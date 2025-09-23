#!/usr/bin/env python3
"""
Test script to verify all API endpoints are working correctly.
Run this script after deployment to ensure the API is functioning properly.
"""

import requests
import json
import time
import os

# Get the base URL from environment or default to localhost
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000").rstrip("/")

def log(message, level="INFO"):
    """Log messages with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

def test_endpoint(method, url, data=None, headers=None, expected_status=200, description=""):
    """Test a single endpoint"""
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=10)
        elif method.upper() == "PATCH":
            response = requests.patch(url, json=data, headers=headers, timeout=10)
        else:
            log(f"Unsupported method: {method}", "ERROR")
            return False

        if response.status_code == expected_status:
            log(f"✅ {description} - Status: {response.status_code}")
            return True
        else:
            log(f"❌ {description} - Expected: {expected_status}, Got: {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            return False

    except Exception as e:
        log(f"❌ {description} - Exception: {str(e)}", "ERROR")
        return False

def run_tests():
    """Run all endpoint tests"""
    log("Starting API endpoint tests...")

    # Test basic endpoints
    tests_passed = 0
    total_tests = 0

    # Root endpoint
    total_tests += 1
    if test_endpoint("GET", f"{BASE_URL}/", description="Root endpoint"):
        tests_passed += 1

    # Health check
    total_tests += 1
    if test_endpoint("GET", f"{BASE_URL}/health", description="Health check"):
        tests_passed += 1

    # Auth endpoints
    # Get all users
    total_tests += 1
    if test_endpoint("GET", f"{BASE_URL}/auth/users", description="Get all users"):
        tests_passed += 1

    # Login (create new user)
    test_phone = "9999999999"
    login_data = {"name": "Test User", "phone": test_phone}
    total_tests += 1
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_data, timeout=15)
    if resp.status_code == 200:
        tests_passed += 1
        log("✅ User login/registration - Status: 200")
        user_info = resp.json()
        user_id = user_info.get("userId") or user_info.get("user", {}).get("id")
    else:
        log(f"❌ User login/registration - Expected: 200, Got: {resp.status_code}", "ERROR")
        log(f"Response: {resp.text}", "ERROR")
        user_id = None

    # Get user by phone
    total_tests += 1
    if test_endpoint("GET", f"{BASE_URL}/auth/user/{test_phone}", description="Get user by phone"):
        tests_passed += 1

    # Events endpoints
    # Get all events
    total_tests += 1
    ev_resp = requests.get(f"{BASE_URL}/events/", timeout=15)
    if ev_resp.status_code == 200:
        tests_passed += 1
        log("✅ Get all events - Status: 200")
        events = ev_resp.json()
    else:
        log(f"❌ Get all events - Expected: 200, Got: {ev_resp.status_code}", "ERROR")
        log(f"Response: {ev_resp.text}", "ERROR")
        events = []

    # Create event (requires auth token, but test basic structure)
    event_data = {
        "title": "Test Event",
        "description": "Test event description",
        "city": "Test City",
        "venue": "Test Venue",
        "startAt": "2025-12-25T10:00:00",
        "endAt": "2025-12-25T12:00:00",
        "priceINR": 100,
        "bannerUrl": "https://example.com/banner.jpg",
        "organizerName": "Test Organizer",
        "organizerLogo": "https://example.com/logo.jpg"
    }
    total_tests += 1
    ce_resp = requests.post(f"{BASE_URL}/events/", json=event_data, timeout=15)
    if ce_resp.status_code == 200:
        tests_passed += 1
        log("✅ Create event - Status: 200")
        created_event = ce_resp.json()
        events.append(created_event)
    else:
        log(f"❌ Create event - Expected: 200, Got: {ce_resp.status_code}", "ERROR")
        log(f"Response: {ce_resp.text}", "ERROR")
        created_event = events[0] if events else None

    # Tickets endpoints
    # Create order
    # Choose an event id to work with
    event_id = (created_event or (events[0] if events else {})).get("id", "")
    total_tests += 1
    if event_id:
        if test_endpoint("POST", f"{BASE_URL}/create-order?phone={test_phone}&eventId={event_id}", expected_status=200, description="Create order"):
            tests_passed += 1
    else:
        log("⚠️  Skipping Create order - no event available", "WARNING")

    # Register for free event
    register_data = {"phone": test_phone, "eventId": event_id}
    total_tests += 1
    reg_resp = requests.post(f"{BASE_URL}/register/free", json=register_data, timeout=20)
    if reg_resp.status_code == 200:
        tests_passed += 1
        log("✅ Register free - Status: 200")
        ticket = reg_resp.json()
    else:
        log(f"❌ Register free - Expected: 200, Got: {reg_resp.status_code}", "ERROR")
        log(f"Response: {reg_resp.text}", "ERROR")
        ticket = None

    # Get tickets for user
    total_tests += 1
    if user_id:
        if test_endpoint("GET", f"{BASE_URL}/tickets/{user_id}", expected_status=200, description="Get user tickets"):
            tests_passed += 1
    else:
        log("⚠️  Skipping Get user tickets - no user id", "WARNING")

    # Validate token
    total_tests += 1
    if ticket and ticket.get("qrToken"):
        validate_data = {"token": ticket["qrToken"], "eventId": event_id}
        if test_endpoint("POST", f"{BASE_URL}/validate", data=validate_data, expected_status=200, description="Validate token"):
            tests_passed += 1
    else:
        # send bad payload to ensure 422
        if test_endpoint("POST", f"{BASE_URL}/validate", data={"token": ""}, expected_status=422, description="Validate token (expected 422)"):
            tests_passed += 1

    # Summary
    log(f"\nTest Summary: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        log("🎉 All tests passed! API is working correctly.", "SUCCESS")
        return True
    else:
        log(f"⚠️  {total_tests - tests_passed} tests failed. Check the logs above.", "WARNING")
        return False

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
