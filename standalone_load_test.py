#!/usr/bin/env python3
"""
Standalone Load Testing Script for Fitness Event Booking API
Simulates 600 concurrent users making various API requests
"""

import asyncio
import aiohttp
import json
import random
import time
import uuid
from datetime import datetime, timedelta
import argparse
import logging
from typing import List, Dict, Any
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoadTester:
    def __init__(self, base_url: str, num_users: int = 600, duration: int = 60):
        self.base_url = base_url.rstrip('/')
        self.num_users = num_users
        self.duration = duration
        self.results = []
        self.errors = []
        self.start_time = None
        self.end_time = None

        # User behavior patterns (weighted)
        self.user_actions = [
            ("get_events", 0.4),           # 40% - List events
            ("get_health", 0.1),           # 10% - Health check
            ("create_user", 0.1),          # 10% - User registration
            ("get_user_tickets", 0.15),    # 15% - Get user tickets
            ("get_cache_stats", 0.05),     # 5% - Cache stats
            ("update_user", 0.1),          # 10% - Update user profile
            ("get_event_by_id", 0.1),      # 10% - Get specific event
        ]

        # Sample data
        self.sample_users = [
            {"name": f"User{i}", "phone": f"98765{i%10000:04d}"}
            for i in range(100)
        ]

        self.sample_events = [
            {
                "title": f"Test Event {i}",
                "description": f"Test event description {i}",
                "city": random.choice(["Mumbai", "Delhi", "Bangalore", "Chennai", "Pune"]),
                "venue": f"Test Venue {i}",
                "startAt": (datetime.now() + timedelta(days=i%30)).isoformat(),
                "endAt": (datetime.now() + timedelta(days=i%30+1)).isoformat(),
                "priceINR": random.randint(100, 1000),
                "coordinate_lat": f"{random.uniform(8, 37):.6f}",
                "coordinate_long": f"{random.uniform(68, 97):.6f}"
            }
            for i in range(20)
        ]

    def get_random_user(self) -> Dict[str, str]:
        """Get a random user for testing"""
        return random.choice(self.sample_users)

    def get_random_event(self) -> Dict[str, Any]:
        """Get a random event for testing"""
        return random.choice(self.sample_events)

    def select_action(self) -> str:
        """Select a random action based on weights"""
        actions, weights = zip(*self.user_actions)
        return random.choices(actions, weights=weights)[0]

    async def make_request(self, session: aiohttp.ClientSession, user_id: str) -> Dict[str, Any]:
        """Make a single request based on user behavior"""
        action = self.select_action()

        try:
            if action == "get_events":
                # GET /events/
                async with session.get(f"{self.base_url}/events/") as response:
                    return {
                        "user_id": user_id,
                        "action": "get_events",
                        "status": response.status,
                        "duration": time.time(),
                        "success": response.status == 200
                    }

            elif action == "get_health":
                # GET /health
                async with session.get(f"{self.base_url}/health") as response:
                    return {
                        "user_id": user_id,
                        "action": "get_health",
                        "status": response.status,
                        "duration": time.time(),
                        "success": response.status == 200
                    }

            elif action == "create_user":
                # POST /auth/login (register new user)
                user_data = self.get_random_user()
                async with session.post(
                    f"{self.base_url}/auth/login",
                    json=user_data
                ) as response:
                    return {
                        "user_id": user_id,
                        "action": "create_user",
                        "status": response.status,
                        "duration": time.time(),
                        "success": response.status in [200, 201]
                    }

            elif action == "get_user_tickets":
                # GET /tickets/{user_id}
                async with session.get(f"{self.base_url}/tickets/{user_id}") as response:
                    return {
                        "user_id": user_id,
                        "action": "get_user_tickets",
                        "status": response.status,
                        "duration": time.time(),
                        "success": response.status == 200
                    }

            elif action == "get_cache_stats":
                # GET /cache-stats
                async with session.get(f"{self.base_url}/cache-stats") as response:
                    return {
                        "user_id": user_id,
                        "action": "get_cache_stats",
                        "status": response.status,
                        "duration": time.time(),
                        "success": response.status == 200
                    }

            elif action == "update_user":
                # PUT /auth/user/{user_id}
                update_data = {
                    "name": f"Updated User {random.randint(1, 1000)}",
                    "bio": f"Updated bio for user {user_id}"
                }
                async with session.put(
                    f"{self.base_url}/auth/user/{user_id}",
                    data=update_data
                ) as response:
                    return {
                        "user_id": user_id,
                        "action": "update_user",
                        "status": response.status,
                        "duration": time.time(),
                        "success": response.status == 200
                    }

            elif action == "get_event_by_id":
                # GET /events/{event_id}
                event = self.get_random_event()
                event_id = event["title"].replace(" ", "_").lower() + "_test"
                async with session.get(f"{self.base_url}/events/{event_id}") as response:
                    return {
                        "user_id": user_id,
                        "action": "get_event_by_id",
                        "status": response.status,
                        "duration": time.time(),
                        "success": response.status in [200, 404]  # 404 is acceptable for test events
                    }

        except Exception as e:
            return {
                "user_id": user_id,
                "action": action,
                "status": 0,
                "duration": time.time(),
                "success": False,
                "error": str(e)
            }

    async def simulate_user(self, session: aiohttp.ClientSession, user_id: str) -> List[Dict[str, Any]]:
        """Simulate a single user making requests"""
        user_results = []
        end_time = time.time() + self.duration

        while time.time() < end_time:
            # Random delay between requests (0.1 to 2 seconds)
            delay = random.uniform(0.1, 2.0)
            await asyncio.sleep(delay)

            result = await self.make_request(session, user_id)
            user_results.append(result)

        return user_results

    async def run_load_test(self):
        """Run the complete load test"""
        print("🚀 Starting Load Test...")
        print(f"📊 Target: {self.num_users} concurrent users")
        print(f"⏱️  Duration: {self.duration} seconds")
        print(f"🌐 Backend: {self.base_url}")
        print("-" * 60)

        self.start_time = time.time()

        # Create connector with limits
        connector = aiohttp.TCPConnector(
            limit=self.num_users,  # Connection pool size
            limit_per_host=self.num_users,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=60
        )

        # Configure session
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:
            # Create tasks for all users
            tasks = [
                self.simulate_user(session, f"user_{i}")
                for i in range(self.num_users)
            ]

            # Run all tasks concurrently
            print(f"🎯 Starting {self.num_users} concurrent users...")
            all_results = await asyncio.gather(*tasks, return_exceptions=True)

        self.end_time = time.time()

        # Process results
        self.process_results(all_results)

    def process_results(self, all_results: List[List[Dict[str, Any]]]):
        """Process and analyze test results"""
        print("\n" + "="*60)
        print("📈 LOAD TEST RESULTS")
        print("="*60)

        # Flatten results
        flat_results = []
        for user_results in all_results:
            if isinstance(user_results, list):
                flat_results.extend(user_results)

        self.results = flat_results

        # Calculate statistics
        total_requests = len(flat_results)
        successful_requests = sum(1 for r in flat_results if r.get("success", False))
        failed_requests = total_requests - successful_requests
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0

        # Response times
        response_times = [r.get("duration", 0) for r in flat_results if "duration" in r]
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0

        # Requests per second
        duration = self.end_time - self.start_time if self.end_time and self.start_time else self.duration
        rps = total_requests / duration if duration > 0 else 0

        # Action breakdown
        action_counts = {}
        for result in flat_results:
            action = result.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

        # Error analysis
        error_counts = {}
        for result in flat_results:
            if not result.get("success", False):
                error = result.get("error", "unknown")
                status = result.get("status", 0)
                error_key = f"{status}: {error}" if error != "unknown" else f"Status {status}"
                error_counts[error_key] = error_counts.get(error_key, 0) + 1

        # Print summary
        print(f"⏱️  Test Duration: {duration:.2f} seconds")
        print(f"📊 Total Requests: {total_requests:,}")
        print(f"✅ Successful: {successful_requests:,} ({success_rate:.1f}%)")
        print(f"❌ Failed: {failed_requests:,}")
        print(f"⚡ Requests/sec: {rps:.1f}")
        print()

        print("📈 RESPONSE TIMES:")
        print(f"   Average: {avg_response_time:.3f}s")
        print(f"   Min: {min_response_time:.3f}s")
        print(f"   Max: {max_response_time:.3f}s")
        print(f"   95th percentile: {p95_response_time:.3f}s")
        print()

        print("🎯 ACTION BREAKDOWN:")
        for action, count in sorted(action_counts.items()):
            percentage = (count / total_requests * 100) if total_requests > 0 else 0
            print(f"   {action}: {count:,} ({percentage:.1f}%)")
        print()

        if error_counts:
            print("🚨 ERROR ANALYSIS:")
            for error, count in sorted(error_counts.items()):
                percentage = (count / total_requests * 100) if total_requests > 0 else 0
                print(f"   {error}: {count:,} ({percentage:.1f}%)")
        else:
            print("✅ No errors detected!")

        print("\n" + "="*60)

        # Performance assessment
        if success_rate >= 99 and p95_response_time < 1.0:
            print("🎉 EXCELLENT PERFORMANCE!")
        elif success_rate >= 95 and p95_response_time < 2.0:
            print("👍 GOOD PERFORMANCE")
        elif success_rate >= 90:
            print("⚠️  ACCEPTABLE PERFORMANCE")
        else:
            print("❌ POOR PERFORMANCE - Needs optimization")

        print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Load Test Script for Fitness Event Booking API")
    parser.add_argument("url", help="Railway backend URL (e.g., https://your-app.railway.app)")
    parser.add_argument("--users", type=int, default=600, help="Number of concurrent users (default: 600)")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds (default: 60)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("🚀 Fitness Event Booking API - Load Testing Tool")
    print("=" * 60)
    print(f"🎯 Target URL: {args.url}")
    print(f"👥 Users: {args.users}")
    print(f"⏱️  Duration: {args.duration} seconds")
    print("=" * 60)

    # Validate and fix URL
    if not args.url.startswith("http"):
        if args.url.startswith("localhost") or args.url.startswith("127.0.0.1"):
            args.url = f"http://{args.url}"
        else:
            args.url = f"https://{args.url}"
        print(f"🔧 Fixed URL: {args.url}")

    # Create and run load tester
    tester = LoadTester(args.url, args.users, args.duration)

    try:
        asyncio.run(tester.run_load_test())
    except KeyboardInterrupt:
        print("\n🛑 Load test interrupted by user")
    except Exception as e:
        print(f"\n❌ Load test failed: {e}")

if __name__ == "__main__":
    main()
