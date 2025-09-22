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
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")

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
    login_data = {"name": "Test User", "phone": "9999999999"}
    total_tests += 1
    if test_endpoint("POST", f"{BASE_URL}/auth/login", data=login_data, description="User login/registration"):
        tests_passed += 1

    # Get user by phone
    total_tests += 1
    if test_endpoint("GET", f"{BASE_URL}/auth/user/9999999999", description="Get user by phone"):
        tests_passed += 1

    # Events endpoints
    # Get all events
    total_tests += 1
    if test_endpoint("GET", f"{BASE_URL}/events/", description="Get all events"):
        tests_passed += 1

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
    if test_endpoint("POST", f"{BASE_URL}/events/", data=event_data, expected_status=200, description="Create event"):
        tests_passed += 1

    # Tickets endpoints
    # Create order
    total_tests += 1
    if test_endpoint("POST", f"{BASE_URL}/create-order?phone=9999999999&eventId=evt_test", expected_status=200, description="Create order"):
        tests_passed += 1

    # Register for free event
    register_data = {"phone": "9999999999", "eventId": "evt_test"}
    total_tests += 1
    if test_endpoint("POST", f"{BASE_URL}/register/free", data=register_data, expected_status=200, description="Register free"):
        tests_passed += 1

    # Get tickets for user
    total_tests += 1
    if test_endpoint("GET", f"{BASE_URL}/tickets/u_test", expected_status=200, description="Get user tickets"):
        tests_passed += 1

    # Validate token
    validate_data = {"token": "test.jwt.token", "device": "test-device", "operator": "test-op"}
    total_tests += 1
    if test_endpoint("POST", f"{BASE_URL}/validate", data=validate_data, expected_status=422, description="Validate token (expected validation error)"):
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
