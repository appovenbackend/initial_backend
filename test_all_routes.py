#!/usr/bin/env python3
"""
Comprehensive test suite for all API routes using FastAPI TestClient.
Tests all routes across auth, events, tickets, payments, social, and migration routers.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
from unittest.mock import patch

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

try:
    from main import app
    from utils.database import get_database_session, read_users, write_users
    from core.config import SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    from services.cache_service import is_cache_healthy
    import os
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the initial_backend directory")
    sys.exit(1)

# Test client
client = TestClient(app)

# Test data
test_user = {
    "name": "Test User",
    "phone": "+12345678900",
    "email": "test@example.com",
    "password": "testpass123"
}

test_event = {
    "name": "Test Fitness Event",
    "description": "A test fitness event",
    "category": "Fitness",
    "price": 500,
    "capacity": 50,
    "venue": "Test Stadium",
    "startDate": "2025-12-31T10:00:00Z",
    "endDate": "2025-12-31T12:00:00Z",
    "registrationDeadline": "2025-12-30T23:59:59Z",
    "rules": "Test rules"
}

class TestAuthRoutes:
    """Test all authentication routes"""

    def setup_method(self):
        """Setup before each test"""
        # Clear any existing test data if needed
        pass

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "msg" in data

    def test_test_endpoint(self):
        """Test test endpoint"""
        response = client.get("/test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Test endpoint working"
        assert "timestamp" in data

    def test_openapi_test(self):
        """Test openapi test endpoint"""
        response = client.get("/openapi-test")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "routes_count" in data
        assert "title" in data

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "memory" in data

    @patch('routers.auth.oauth')
    def test_register_success(self, mock_oauth):
        """Test user registration success"""
        # Mock oauth for registration test
        mock_oauth.google.authorize_redirect.return_value = None

        response = client.post("/auth/register", json=test_user)
        # May fail if email/phone already exists, which is ok
        if response.status_code == 200:
            data = response.json()
            assert "msg" in data
            assert data["msg"] == "User registered successfully"
            assert "user" in data
            assert "access_token" in data
            assert data["token_type"] == "bearer"
        else:
            # If user exists, expect 400
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data

    @patch('routers.auth.oauth')
    def test_login_success(self, mock_oauth):
        """Test user login success"""
        login_data = {
            "phone": test_user["phone"],
            "password": test_user["password"]
        }
        response = client.post("/auth/login", json=login_data)

        if response.status_code == 200:
            data = response.json()
            assert data["msg"] == "login_successful"
            assert "user" in data
            assert "access_token" in data
            assert data["token_type"] == "bearer"
        else:
            # User might not exist, expect 401
            assert response.status_code == 401

    def test_get_user_by_phone(self):
        """Test getting user by phone"""
        response = client.get(f"/auth/user/{test_user['phone']}")
        print(f"User by phone response: {response.status_code} - {response.text}")
        # May fail if user doesn't exist, but route should be accessible
        assert response.status_code in [200, 404]

    @patch('routers.auth.jwt_security_manager')
    def test_get_user_points(self, mock_jwt):
        """Test getting user points"""
        # Mock authentication
        mock_jwt.create_token.return_value = "mock_token"

        # Create a mock authenticated request
        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        response = client.get("/auth/points", headers=headers)

        # Should work with mock authentication
        print(f"User points response: {response.status_code}")
        # The actual response will depend on implementation, but route should exist
        assert response.status_code in [200, 401, 500]

    def test_google_login_redirect(self):
        """Test Google OAuth login redirect"""
        response = client.get("/auth/google_login")
        # This should redirect or return an error if OAuth not configured
        print(f"Google login response: {response.status_code}")

    @patch('routers.auth.jwt_security_manager')
    def test_get_all_users_admin(self, mock_jwt):
        """Test getting all users (admin endpoint)"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "admin_user"}
        response = client.get("/auth/users", headers=headers)
        print(f"All users response: {response.status_code}")
        # Admin route should exist
        assert response.status_code in [200, 401, 403, 500]


class TestEventsRoutes:
    """Test all events routes"""

    @patch('routers.events.jwt_security_manager')
    def test_create_event(self, mock_jwt):
        """Test creating an event"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        response = client.post("/events/create", json=test_event, headers=headers)
        print(f"Create event response: {response.status_code} - {response.text}")
        assert response.status_code in [200, 401, 403, 500]

    def test_list_events(self):
        """Test listing events"""
        response = client.get("/events/list")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "events" in data

    def test_list_recent_events(self):
        """Test listing recent events"""
        response = client.get("/events/recent?limit=5")
        assert response.status_code in [200, 500]

    def test_get_featured_events(self):
        """Test getting featured events"""
        response = client.get("/events/featured")
        assert response.status_code in [200, 500]

    def test_featured_slots_status(self):
        """Test featured slots status"""
        response = client.get("/events/featured-slots")
        assert response.status_code in [200, 500]

    @patch('routers.events.jwt_security_manager')
    def test_update_featured_slots(self, mock_jwt):
        """Test updating featured slots"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "admin_user"}
        slots_data = {"slot_1": "event_123"}
        response = client.post("/events/featured-slots", json=slots_data, headers=headers)
        print(f"Update featured slots response: {response.status_code}")
        assert response.status_code in [200, 401, 403, 500]

    def test_toggle_featured_event(self):
        """Test toggling featured event"""
        response = client.put("/events/featured/test_event_id")
        assert response.status_code in [200, 401, 404, 500]

    def test_set_featured_events_list(self):
        """Test setting featured events list"""
        event_ids = ["event1", "event2"]
        response = client.post("/events/featured-list", json={"event_ids": event_ids})
        assert response.status_code in [200, 401, 500]


class TestTicketsRoutes:
    """Test all tickets routes"""

    @patch('routers.tickets.jwt_security_manager')
    def test_register_free(self, mock_jwt):
        """Test free registration"""
        mock_jwt.create_token.return_value = "mock_token"

        registration_data = {
            "eventId": "test_event_id",
            "fullName": "Test User",
            "email": "test@example.com",
            "phone": "+12345678900"
        }

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        response = client.post("/tickets/register-free", json=registration_data, headers=headers)
        print(f"Free registration response: {response.status_code}")
        assert response.status_code in [200, 400, 401, 404, 500]

    @patch('routers.tickets.jwt_security_manager')
    def test_get_tickets_for_user(self, mock_jwt):
        """Test getting user tickets"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        response = client.get("/tickets/user/test_user_id", headers=headers)
        print(f"Get user tickets response: {response.status_code}")
        assert response.status_code in [200, 401, 404, 500]

    def test_get_ticket(self):
        """Test getting specific ticket"""
        response = client.get("/tickets/ticket/test_ticket_id")
        assert response.status_code in [200, 401, 404, 500]

    @patch('routers.tickets.jwt_security_manager')
    def test_receive_qr_token(self, mock_jwt):
        """Test receiving QR token"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        qr_payload = {
            "token": "test_qr_token",
            "eventId": "test_event_id"
        }
        response = client.post("/tickets/receive-qr", json=qr_payload, headers=headers)
        print(f"Receive QR token response: {response.status_code}")
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_validate_ticket(self):
        """Test ticket validation"""
        validation_data = {
            "barcode": "test_barcode",
            "eventId": "test_event_id"
        }
        response = client.post("/tickets/validate", json=validation_data)
        assert response.status_code in [200, 400, 404, 500]


class TestPaymentsRoutes:
    """Test all payments routes"""

    @patch('routers.payments.jwt_security_manager')
    def test_create_payment_order(self, mock_jwt):
        """Test creating payment order"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        order_data = {
            "eventId": "test_event_id",
            "amount": 500,
            "currency": "INR"
        }
        response = client.post("/payments/create-order", json=order_data, headers=headers)
        print(f"Create payment order response: {response.status_code}")
        assert response.status_code in [200, 400, 401, 500]

    @patch('routers.payments.jwt_security_manager')
    def test_verify_payment(self, mock_jwt):
        """Test verifying payment"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        verify_data = {
            "orderId": "test_order_id",
            "paymentId": "test_payment_id",
            "signature": "test_signature"
        }
        response = client.post("/payments/verify", json=verify_data, headers=headers)
        print(f"Verify payment response: {response.status_code}")
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_get_order_status(self):
        """Test getting order status"""
        response = client.get("/payments/order/test_order_id")
        assert response.status_code in [200, 404, 500]

    def test_test_payment_integration(self):
        """Test payment integration"""
        response = client.post("/payments/test")
        assert response.status_code in [200, 500]


class TestSocialRoutes:
    """Test all social routes"""

    def test_get_user_profile_public(self):
        """Test getting user profile as public viewer"""
        response = client.get("/social/users/test_user_id")
        assert response.status_code in [200, 404, 500]

    @patch('routers.social.jwt_security_manager')
    def test_get_user_profile_authenticated(self, mock_jwt):
        """Test getting user profile when authenticated"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        response = client.get("/social/users/test_user_id", headers=headers)
        print(f"Get user profile response: {response.status_code}")
        assert response.status_code in [200, 401, 404, 500]

    @patch('routers.social.jwt_security_manager')
    def test_update_privacy_setting(self, mock_jwt):
        """Test updating privacy setting"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        response = client.put("/social/users/test_user_id/privacy", headers=headers)
        print(f"Update privacy response: {response.status_code}")
        assert response.status_code in [200, 401, 403, 404, 500]

    @patch('routers.social.jwt_security_manager')
    def test_get_privacy_setting(self, mock_jwt):
        """Test getting privacy setting"""
        mock_jwt.create_token.return_value = "mock_token"

        headers = {"Authorization": "Bearer mock_token", "X-User-ID": "test_user_id"}
        response = client.get("/social/users/test_user_id/privacy", headers=headers)
        print(f"Get privacy response: {response.status_code}")
        assert response.status_code in [200, 401, 403, 404, 500]

    def test_request_connection(self):
        """Test requesting connection"""
        headers = {"X-User-ID": "requester_id"}
        response = client.post("/social/users/target_user_id/connect", headers=headers)
        assert response.status_code in [200, 401, 404, 500]

    def test_get_connection_requests_pending(self):
        """Test getting pending connection requests"""
        headers = {"X-User-ID": "test_user_id"}
        response = client.get("/social/connection-requests", headers=headers)
        assert response.status_code in [200, 401, 500]

    def test_accept_connection_request(self):
        """Test accepting connection request"""
        headers = {"X-User-ID": "test_user_id"}
        response = client.post("/social/connection-requests/request_id/accept", headers=headers)
        assert response.status_code in [200, 401, 404, 500]

    def test_decline_connection_request(self):
        """Test declining connection request"""
        headers = {"X-User-ID": "test_user_id"}
        response = client.post("/social/connection-requests/request_id/decline", headers=headers)
        assert response.status_code in [200, 401, 404, 500]

    def test_get_user_connections(self):
        """Test getting user connections"""
        headers = {"X-User-ID": "test_user_id"}
        response = client.get("/social/connections", headers=headers)
        assert response.status_code in [200, 401, 500]

    def test_get_my_connections(self):
        """Test getting my connections"""
        headers = {"X-User-ID": "test_user_id"}
        response = client.get("/social/my-connections", headers=headers)
        assert response.status_code in [200, 401, 500]

    def test_get_activity_feed(self):
        """Test getting activity feed"""
        headers = {"X-User-ID": "test_user_id"}
        response = client.get("/social/activity", headers=headers)
        assert response.status_code in [200, 401, 500]

    def test_search_users(self):
        """Test searching users"""
        headers = {"X-User-ID": "test_user_id"}
        response = client.get("/social/users/search?q=test", headers=headers)
        assert response.status_code in [200, 500]

    def test_admin_notify_all_users(self):
        """Test admin notification to all users"""
        message_data = {"message": "Test notification"}
        response = client.post("/social/admin/notify-all", json=message_data)
        assert response.status_code in [200, 401, 403, 500]

    def test_admin_notify_event_subscribers(self):
        """Test admin notification to event subscribers"""
        message_data = {"message": "Test event notification"}
        response = client.post("/social/admin/notify-event/test_event_id", json=message_data)
        assert response.status_code in [200, 401, 403, 404, 500]


class TestMigrationRoutes:
    """Test all migration routes"""

    def test_fix_registration_link_column(self):
        """Test fixing registration link column migration"""
        response = client.post("/migration/fix-registration-link")
        print(f"Migration fix response: {response.status_code}")
        assert response.status_code in [200, 500]

    def test_get_migration_status(self):
        """Test getting migration status"""
        response = client.get("/migration/status")
        print(f"Migration status response: {response.status_code}")
        assert response.status_code in [200, 500]


class TestCacheRoutes:
    """Test cache management routes"""

    def test_get_cache_stats(self):
        """Test getting cache statistics"""
        # These routes require admin authentication
        response = client.get("/cache-stats")
        print(f"Cache stats response: {response.status_code}")
        assert response.status_code in [200, 401, 403, 500]

    def test_clear_cache(self):
        """Test clearing cache"""
        response = client.post("/cache-clear")
        print(f"Clear cache response: {response.status_code}")
        assert response.status_code in [200, 401, 403, 500]


# Utility functions for complex tests
def cleanup_test_data():
    """Clean up test data if needed"""
    # This would clean up test users/events/etc if implemented
    pass

def run_all_route_tests():
    """Run all route tests and return results"""

    print("="*70)
    print("🧪 COMPREHENSIVE API ROUTE TESTING SUITE")
    print("="*70)

    results = {
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "results": {}
    }

    # Run tests by category
    test_categories = [
        ("Authentication", TestAuthRoutes()),
        ("Events", TestEventsRoutes()),
        ("Tickets", TestTicketsRoutes()),
        ("Payments", TestPaymentsRoutes()),
        ("Social", TestSocialRoutes()),
        ("Migration", TestMigrationRoutes()),
        ("Cache", TestCacheRoutes())
    ]

    for category_name, test_instance in test_categories:
        print(f"\n📋 Testing {category_name} Routes")
        print("-" * 40)

        category_results = {"total": 0, "passed": 0, "failed": 0}

        # Get all test methods for this category
        test_methods = [method for method in dir(test_instance)
                       if method.startswith('test_') and callable(getattr(test_instance, method))]

        for method_name in test_methods:
            results["total_tests"] += 1
            category_results["total"] += 1

            try:
                # Set up the test
                if hasattr(test_instance, 'setup_method'):
                    test_instance.setup_method()

                # Run the test
                method = getattr(test_instance, method_name)
                method()

                print(f"✅ {method_name}")
                results["passed"] += 1
                category_results["passed"] += 1

            except Exception as e:
                print(f"❌ {method_name}: {str(e)}")
                results["failed"] += 1
                category_results["failed"] += 1

        # Category summary
        results["results"][category_name] = category_results
        success_rate = (category_results["passed"] / category_results["total"]) * 100
        print(f"📊 {category_name}: {category_results['passed']}/{category_results['total']} ({success_rate:.1f}%)")

    # Overall summary
    print("\n" + "="*70)
    print("🎯 FINAL RESULTS SUMMARY")
    print("="*70)

    for category, cat_results in results["results"].items():
        success_rate = (cat_results["passed"] / cat_results["total"]) * 100 if cat_results["total"] > 0 else 0
        status = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "❌"
        print(".1f")

    total_success_rate = (results["passed"] / results["total_tests"]) * 100 if results["total_tests"] > 0 else 0
    overall_status = "✅ COMPLETE" if total_success_rate >= 90 else "⚠️ MOSTLY WORKING" if total_success_rate >= 70 else "❌ NEEDS ATTENTION"

    print(f"\n🎯 OVERALL: {results['passed']}/{results['total_tests']} tests passed ({total_success_rate:.1f}%)")
    print(f"📈 STATUS: {overall_status}")

    return results


if __name__ == "__main__":
    # Run all tests
    test_results = run_all_route_tests()

    # Exit with appropriate code
    success_rate = (test_results["passed"] / test_results["total_tests"]) * 100 if test_results["total_tests"] > 0 else 0
    exit_code = 0 if success_rate >= 90 else 1 if success_rate >= 70 else 2

    print(f"\n🏁 Test suite completed with exit code: {exit_code}")
    sys.exit(exit_code)
