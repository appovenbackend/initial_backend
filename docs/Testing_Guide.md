# Testing Guide

## 📋 Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [Load Testing](#load-testing)
5. [Security Testing](#security-testing)
6. [Test Environment Setup](#test-environment-setup)
7. [Automated Testing](#automated-testing)
8. [Performance Testing](#performance-testing)
9. [Test Data Management](#test-data-management)
10. [Continuous Integration](#continuous-integration)

## 🧪 Testing Strategy

### Testing Pyramid

```mermaid
graph TD
    A[Unit Tests] --> B[Integration Tests]
    B --> C[API Tests]
    C --> D[Load Tests]
    D --> E[Security Tests]

    A --> F[80% Test Coverage]
    B --> G[20% Test Coverage]
    C --> H[Minimal Coverage]
    D --> I[Performance Benchmarks]
    E --> J[Security Validation]
```

### Test Categories

| Test Type | Purpose | Tools | Frequency |
|-----------|---------|-------|-----------|
| **Unit Tests** | Test individual functions/components | pytest | Every commit |
| **Integration Tests** | Test API endpoints and database | pytest, httpx | Every commit |
| **Load Tests** | Test system performance | locust, artillery | Before deployment |
| **Security Tests** | Test for vulnerabilities | OWASP ZAP, sqlmap | Before deployment |
| **Smoke Tests** | Basic functionality verification | curl, pytest | Every deployment |

## 🏃‍♂️ Unit Tests

### Setting Up Unit Tests

**Install Test Dependencies:**
```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

**Test Configuration:**
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --cov=app
    --cov-report=html
    --cov-report=term-missing
```

### Writing Unit Tests

**Example: Authentication Service Test**
```python
# tests/test_auth_service.py
import pytest
from unittest.mock import Mock, patch
from services.auth_service import AuthenticationService
from core.security import hash_password, verify_password

class TestAuthenticationService:
    def setup_method(self):
        self.auth_service = AuthenticationService()

    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed)

    def test_verify_password_wrong_password(self):
        """Test password verification with wrong password"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert not verify_password(wrong_password, hashed)

    @patch('services.auth_service.send_sms')
    def test_send_otp_success(self, mock_send_sms):
        """Test OTP sending"""
        mock_send_sms.return_value = True

        result = self.auth_service.send_otp("+919876543210")

        assert result["success"] is True
        assert "otp" in result
        mock_send_sms.assert_called_once()

    def test_send_otp_invalid_phone(self):
        """Test OTP sending with invalid phone"""
        result = self.auth_service.send_otp("invalid_phone")

        assert result["success"] is False
        assert result["error"] == "Invalid phone number"
```

**Example: Database Model Test**
```python
# tests/test_models.py
import pytest
from models.user import User
from models.event import Event

class TestUserModel:
    def test_create_user(self):
        """Test user creation"""
        user = User(
            id="u_test123",
            name="Test User",
            phone="+919876543210",
            email="test@example.com"
        )

        assert user.id == "u_test123"
        assert user.name == "Test User"
        assert user.phone == "+919876543210"

    def test_user_points_calculation(self):
        """Test points calculation for events"""
        # Free event should give 2 points
        points = User.calculate_points(0)
        assert points == 2

        # Paid event should give ceil(price/100) + 2 points
        points = User.calculate_points(250)
        assert points == 5  # ceil(250/100) + 2 = 3 + 2 = 5
```

## 🔗 Integration Tests

### API Endpoint Testing

**Test Setup:**
```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from main import app

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_user(async_client):
    # Create test user
    user_data = {
        "name": "Test User",
        "phone": "+919876543210",
        "email": "test@example.com",
        "password": "testpass123"
    }
    response = await async_client.post("/auth/register", json=user_data)
    return response.json()
```

**Authentication Tests:**
```python
# tests/test_auth_integration.py
import pytest

class TestAuthenticationIntegration:
    async def test_user_registration_and_login(self, async_client):
        """Test complete registration and login flow"""
        # Register user
        user_data = {
            "name": "Integration Test User",
            "phone": "+919876543211",
            "email": "integration@example.com",
            "password": "integration_pass_123"
        }

        register_response = await async_client.post("/auth/register", json=user_data)
        assert register_response.status_code == 200
        user_id = register_response.json()["user"]["id"]
        access_token = register_response.json()["access_token"]

        # Login with same credentials
        login_data = {
            "phone": "+919876543211",
            "password": "integration_pass_123"
        }

        login_response = await async_client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        assert login_response.json()["user"]["id"] == user_id

    async def test_protected_endpoint_access(self, async_client, test_user):
        """Test accessing protected endpoints"""
        # Access protected endpoint without token
        response = await async_client.get("/auth/users")
        assert response.status_code == 401

        # Access protected endpoint with valid token
        headers = {"Authorization": f"Bearer {test_user['access_token']}"}
        response = await async_client.get("/auth/users", headers=headers)
        assert response.status_code == 200
```

### Database Integration Tests

**Database Test Setup:**
```python
# tests/test_database_integration.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.database import Base

@pytest.fixture
def db_engine():
    """Create test database engine"""
    engine = create_engine("sqlite:///./test.db")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(db_engine):
    """Create test database session"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()
```

## ⚡ Load Testing

### Load Testing with Locust

**Install Locust:**
```bash
pip install locust
```

**Load Test Configuration:**
```python
# locustfile.py
from locust import HttpUser, task, between
from tests.load_test_data import get_test_users, get_test_events

class FitnessAppUser(HttpUser):
    """Load testing user behavior"""

    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks

    def on_start(self):
        """Called when user starts"""
        self.client.verify = False  # Disable SSL verification for testing
        self.user_data = get_test_users()[0]
        self.login()

    def login(self):
        """Login before running tasks"""
        login_data = {
            "phone": self.user_data["phone"],
            "password": self.user_data["password"]
        }

        response = self.client.post("/auth/login", json=login_data)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            print(f"Login failed: {response.text}")

    @task(10)  # Weight 10 - most common task
    def browse_events(self):
        """Browse events list"""
        response = self.client.get("/events/all?page=1&limit=20")
        assert response.status_code == 200

    @task(5)  # Weight 5 - less common
    def view_event_details(self):
        """View specific event details"""
        event_id = get_test_events()[0]["id"]
        response = self.client.get(f"/events/{event_id}")
        assert response.status_code == 200

    @task(2)  # Weight 2 - least common
    def book_ticket(self):
        """Book event ticket"""
        if hasattr(self, 'token'):
            event_id = get_test_events()[0]["id"]
            booking_data = {
                "event_id": event_id,
                "participant_details": {
                    "name": self.user_data["name"],
                    "phone": self.user_data["phone"],
                    "email": self.user_data["email"]
                }
            }

            response = self.client.post("/tickets/book", json=booking_data, headers=self.headers)
            # Payment required - just check if request accepted
            assert response.status_code in [200, 402]  # 402 Payment Required is OK

    @task(1)  # Weight 1 - rare task
    def update_profile(self):
        """Update user profile"""
        if hasattr(self, 'token'):
            profile_data = {
                "name": f"Updated {self.user_data['name']}",
                "bio": "Updated via load test"
            }

            response = self.client.put(
                f"/auth/user/{self.user_data['id']}",
                data=profile_data,
                headers=self.headers
            )
            assert response.status_code == 200
```

**Run Load Tests:**
```bash
# Simple load test
locust -f locustfile.py --host=http://localhost:8000

# Load test with specific users
locust -f locustfile.py --host=http://localhost:8000 -u 100 -r 10

# Distributed load test
locust -f locustfile.py --master --host=http://localhost:8000
locust -f locustfile.py --slave --host=http://localhost:8000
```

### Load Test Scenarios

**Scenario 1: Normal Load**
- 100 users
- 10 users spawn per second
- Run for 5 minutes

**Scenario 2: Peak Load**
- 1000 users
- 50 users spawn per second
- Run for 10 minutes

**Scenario 3: Stress Test**
- 5000 users
- 100 users spawn per second
- Run until failure

## 🔒 Security Testing

### Automated Security Testing

**SQL Injection Testing:**
```python
# tests/test_security.py
import pytest

class TestSQLInjection:
    async def test_sql_injection_prevention(self, async_client):
        """Test SQL injection prevention"""
        # Malicious payloads
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--"
        ]

        for payload in malicious_inputs:
            user_data = {
                "name": "Test User",
                "phone": payload,  # Inject malicious data
                "email": "test@example.com",
                "password": "testpass123"
            }

            response = await async_client.post("/auth/register", json=user_data)
            # Should either reject or sanitize the input
            assert response.status_code in [400, 422]  # Bad Request or Validation Error

    async def test_xss_prevention(self, async_client):
        """Test XSS prevention"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>"
        ]

        for payload in xss_payloads:
            user_data = {
                "name": payload,
                "phone": "+919876543210",
                "email": "test@example.com",
                "password": "testpass123"
            }

            response = await async_client.post("/auth/register", json=user_data)
            assert response.status_code in [400, 422]
```

### Penetration Testing

**Using OWASP ZAP:**
```bash
# Install OWASP ZAP
docker run -t owasp/zap2docker-stable zap.sh -cmd

# Run automated scan
zap.sh -cmd -autorun /zap/policies/api-scan.policy -t http://localhost:8000
```

**Manual Security Tests:**
- Authentication bypass attempts
- Authorization escalation
- Input validation bypass
- Rate limit circumvention
- Session hijacking attempts

## 🛠️ Test Environment Setup

### Docker Test Environment

**docker-compose.test.yml:**
```yaml
version: '3.8'
services:
  test_db:
    image: postgres:15
    environment:
      POSTGRES_DB: fitness_test
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    ports:
      - "5433:5432"
    volumes:
      - test_postgres_data:/var/lib/postgresql/data

  test_redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    volumes:
      - test_redis_data:/data

  test_app:
    build: .
    environment:
      - ENVIRONMENT=test
      - DATABASE_URL=postgresql://test_user:test_pass@test_db:5432/fitness_test
      - REDIS_URL=redis://test_redis:6379
      - JWT_SECRET=test-secret-key-for-testing-only
    depends_on:
      - test_db
      - test_redis
    volumes:
      - ./tests:/app/tests
      - ./test_data:/app/test_data

volumes:
  test_postgres_data:
  test_redis_data:
```

### Test Database Setup

**Test Database Initialization:**
```python
# tests/setup_test_db.py
from utils.database import Base, get_database_session
from sqlalchemy import create_engine

def setup_test_database():
    """Set up test database with sample data"""
    engine = create_engine("postgresql://test_user:test_pass@localhost:5433/fitness_test")

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Insert test data
    insert_test_users(engine)
    insert_test_events(engine)
    insert_test_tickets(engine)

    print("Test database setup complete!")
```

## 🤖 Automated Testing

### GitHub Actions CI/CD

**.github/workflows/tests.yml:**
```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: fitness_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov

    - name: Setup test database
      run: python tests/setup_test_db.py
      env:
        DATABASE_URL: postgresql://postgres:test_password@localhost:5432/fitness_test

    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=app --cov-report=xml

    - name: Run integration tests
      run: pytest tests/integration/ -v

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

**.pre-commit-config.yaml:**
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 22.10.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 5.0.4
    hooks:
      - id: flake8

  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        args: [tests/unit/]
```

## 📊 Performance Testing

### Performance Benchmarks

**Benchmark Tests:**
```python
# tests/test_performance.py
import pytest
import time
import asyncio
from tests.performance_benchmarks import PerformanceBenchmarks

class TestPerformance:
    @pytest.mark.asyncio
    async def test_event_listing_performance(self, async_client):
        """Test event listing response time"""
        start_time = time.time()

        response = await async_client.get("/events/all?limit=100")

        end_time = time.time()
        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second

    @pytest.mark.asyncio
    async def test_database_query_performance(self, db_session):
        """Test database query performance"""
        start_time = time.time()

        # Execute complex query
        result = db_session.execute("""
            SELECT e.*, u.name as organizer_name
            FROM events e
            JOIN users u ON e.organizer_id = u.id
            WHERE e.start_time > NOW()
            ORDER BY e.start_time
            LIMIT 50
        """)

        end_time = time.time()
        query_time = end_time - start_time

        assert query_time < 0.5  # Should complete within 500ms
        assert len(result.fetchall()) >= 0
```

### Memory Usage Testing

**Memory Leak Detection:**
```python
# tests/test_memory.py
import pytest
import psutil
import os
from memory_profiler import profile

class TestMemoryUsage:
    def get_memory_usage(self):
        """Get current memory usage"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # MB

    def test_memory_usage_after_requests(self, async_client):
        """Test memory usage doesn't grow significantly"""
        initial_memory = self.get_memory_usage()

        # Make multiple requests
        for i in range(100):
            response = await async_client.get("/health")
            assert response.status_code == 200

        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory

        # Memory shouldn't increase by more than 50MB
        assert memory_increase < 50, f"Memory increased by {memory_increase}MB"
```

## 🗂️ Test Data Management

### Test Data Factories

**User Factory:**
```python
# tests/factories.py
import factory
from models.user import User

class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: f"u_test{n"010d"}")
    name = factory.Faker('name')
    phone = factory.Sequence(lambda n: f"+919876543{n"03d"}")
    email = factory.Faker('email')
    role = "user"
    created_at = factory.Faker('date_time')
```

**Event Factory:**
```python
class EventFactory(factory.Factory):
    class Meta:
        model = Event

    id = factory.Sequence(lambda n: f"e_test{n"010d"}")
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('paragraph')
    organizer_id = factory.SubFactory(UserFactory)
    start_time = factory.Faker('future_datetime')
    end_time = factory.LazyAttribute(lambda obj: obj.start_time + timedelta(hours=2))
    location = factory.Faker('city')
    price_inr = factory.Faker('random_int', min=0, max=1000)
    max_participants = factory.Faker('random_int', min=10, max=100)
```

### Test Data Generation

**Generate Test Dataset:**
```python
# tests/generate_test_data.py
from tests.factories import UserFactory, EventFactory, TicketFactory

def generate_test_data(num_users=100, num_events=50, num_tickets=200):
    """Generate comprehensive test dataset"""

    # Generate users
    users = UserFactory.create_batch(num_users)

    # Generate events
    events = []
    for user in users[:num_events//5]:  # 20% of users are organizers
        events.extend(EventFactory.create_batch(3, organizer=user))

    # Generate tickets
    tickets = []
    for event in events:
        num_event_tickets = min(num_tickets // len(events), event.max_participants)
        for user in users[:num_event_tickets]:
            tickets.append(TicketFactory(
                event=event,
                user=user,
                participant_name=user.name
            ))

    return {
        "users": users,
        "events": events,
        "tickets": tickets
    }
```

## 🔄 Continuous Integration

### CI Pipeline Stages

**1. Code Quality Checks:**
```yaml
# .github/workflows/quality.yml
- name: Code formatting check
  run: black --check .

- name: Import sorting check
  run: isort --check-only .

- name: Linting
  run: flake8 .
```

**2. Security Scans:**
```yaml
# .github/workflows/security.yml
- name: Security scan
  run: bandit -r .

- name: Dependency vulnerability check
  run: safety check
```

**3. Test Execution:**
```yaml
# .github/workflows/tests.yml
- name: Run tests
  run: pytest --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

### Test Reporting

**Coverage Reports:**
- HTML coverage reports generated in `htmlcov/`
- Coverage badges for README
- Coverage trends over time

**Test Results:**
- JUnit XML reports for CI integration
- Test execution time tracking
- Flaky test detection and reporting

## 📈 Performance Benchmarks

### Benchmark Tests

**Database Performance Benchmarks:**
```python
# tests/test_benchmarks.py
import pytest
import time
from tests.benchmark_utils import DatabaseBenchmark

class TestDatabasePerformance:
    def test_user_creation_benchmark(self, db_session, benchmark):
        """Benchmark user creation"""
        def create_user():
            user = UserFactory()
            db_session.add(user)
            db_session.commit()
            return user

        # Benchmark should complete within 100ms
        result = benchmark(create_user)
        assert benchmark.stats.stats.mean < 0.1

    def test_event_query_benchmark(self, db_session, benchmark):
        """Benchmark complex event queries"""
        def query_events():
            return db_session.query(Event).join(User).filter(
                Event.start_time > datetime.now()
            ).limit(50).all()

        # Should complete within 50ms
        result = benchmark(query_events)
        assert benchmark.stats.stats.mean < 0.05
```

### Performance Regression Testing

**Track Performance Over Time:**
```python
# tests/test_performance_regression.py
import pytest
from tests.performance_tracker import PerformanceTracker

class TestPerformanceRegression:
    def test_api_response_time_regression(self):
        """Ensure API response times don't regress"""
        tracker = PerformanceTracker()

        # Get current performance
        current_times = tracker.measure_endpoint_response_times()

        # Compare with baseline
        baseline = tracker.get_baseline_performance()

        for endpoint, current_time in current_times.items():
            baseline_time = baseline.get(endpoint, 0)

            if baseline_time > 0:
                # Allow 20% regression
                max_allowed_time = baseline_time * 1.2
                assert current_time <= max_allowed_time, \
                    f"Performance regression detected for {endpoint}"
```

## 🚨 Troubleshooting Tests

### Common Test Issues

**1. Database Connection Issues:**
```python
# tests/test_db_connection.py
def test_database_connection():
    """Test database connectivity"""
    try:
        engine = create_engine(os.getenv('DATABASE_URL'))
        with engine.connect() as conn:
            result = conn.execute(text('SELECT 1'))
            assert result.fetchone()[0] == 1
    except Exception as e:
        pytest.fail(f"Database connection failed: {e}")
```

**2. Async Test Issues:**
```python
# tests/test_async_issues.py
import pytest

class TestAsyncIssues:
    def test_async_function_timeout(self):
        """Test that async functions don't hang"""
        async def slow_operation():
            await asyncio.sleep(0.1)
            return "completed"

        # Should complete within 1 second
        result = await asyncio.wait_for(slow_operation(), timeout=1.0)
        assert result == "completed"
```

**3. Test Data Cleanup:**
```python
# tests/test_cleanup.py
import pytest

class TestDataCleanup:
    def test_no_orphaned_data(self, db_session):
        """Ensure no test data is left behind"""
        # Count records before test
        initial_count = db_session.query(User).count()

        # Run test that creates data
        user = UserFactory()
        db_session.add(user)
        db_session.commit()

        # Verify data was created
        assert db_session.query(User).count() == initial_count + 1

        # Clean up
        db_session.delete(user)
        db_session.commit()

        # Verify cleanup
        assert db_session.query(User).count() == initial_count
```

## 📋 Test Checklist

### Pre-Deployment Tests

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Load tests pass under expected load
- [ ] Security tests pass
- [ ] Performance benchmarks met
- [ ] No flaky tests detected
- [ ] Test coverage above 80%
- [ ] Database migrations tested

### Test Maintenance

- [ ] Update tests when APIs change
- [ ] Review and fix flaky tests
- [ ] Update test data as needed
- [ ] Monitor test execution times
- [ ] Archive old test results
- [ ] Document test procedures

---

## 📞 Support

For testing issues:
- Check test logs for detailed error information
- Verify test environment configuration
- Ensure test dependencies are installed
- Review test data setup procedures

---

*Last Updated: January 2025*
*Testing Version: v2.0.0*
