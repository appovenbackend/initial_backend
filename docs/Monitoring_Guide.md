# Monitoring & Health Checks Guide

## 📋 Table of Contents

1. [Health Check System](#health-check-system)
2. [Application Monitoring](#application-monitoring)
3. [Database Monitoring](#database-monitoring)
4. [Performance Monitoring](#performance-monitoring)
5. [Security Monitoring](#security-monitoring)
6. [Business Metrics](#business-metrics)
7. [Alert Configuration](#alert-configuration)
8. [Dashboard Setup](#dashboard-setup)
9. [Log Management](#log-management)
10. [Incident Response](#incident-response)

## 🏥 Health Check System

### Comprehensive Health Check

**Health Check Endpoint:**
```http
GET /health
```

**Response Structure:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-04T16:14:11+05:30",
  "database": {
    "type": "PostgreSQL",
    "connection_test": "passed",
    "users_count": 1250,
    "response_time_ms": 15
  },
  "redis": {
    "healthy": true,
    "response_time_ms": 8,
    "memory_used_mb": 45
  },
  "file_system": {
    "accessible": true,
    "uploads_size_mb": 256
  },
  "memory": {
    "total_mb": 8192,
    "available_mb": 4096,
    "percent_used": 50.0
  },
  "uptime_seconds": 3600
}
```

### Health Check Implementation

**Health Check Service:**
```python
# services/health_service.py
import time
import psutil
from sqlalchemy import text
from utils.database import get_database_session
from services.cache_service import is_cache_healthy
import os

class HealthService:
    @staticmethod
    async def comprehensive_health_check() -> dict:
        """Perform comprehensive health check"""
        start_time = time.time()

        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(IST).isoformat(),
            "checks": {}
        }

        # Database health
        db_health = await HealthService.check_database()
        health_status["database"] = db_health
        if not db_health["healthy"]:
            health_status["status"] = "unhealthy"

        # Redis health
        redis_health = await HealthService.check_redis()
        health_status["redis"] = redis_health
        if not redis_health["healthy"]:
            health_status["status"] = "unhealthy"

        # File system health
        fs_health = HealthService.check_file_system()
        health_status["file_system"] = fs_health
        if not fs_health["healthy"]:
            health_status["status"] = "unhealthy"

        # Memory health
        memory_health = HealthService.check_memory()
        health_status["memory"] = memory_health
        if not memory_health["healthy"]:
            health_status["status"] = "degraded"

        # Calculate total response time
        health_status["response_time_ms"] = int((time.time() - start_time) * 1000)

        return health_status

    @staticmethod
    async def check_database() -> dict:
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            db = get_database_session()

            # Test connection
            result = db.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            db.close()

            # Get user count for basic data validation
            from utils.database import read_users
            users_count = len(read_users())

            response_time = int((time.time() - start_time) * 1000)

            return {
                "healthy": True,
                "type": "PostgreSQL" if USE_POSTGRESQL else "SQLite",
                "connection_test": "passed",
                "users_count": users_count,
                "response_time_ms": response_time
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "type": "PostgreSQL" if USE_POSTGRESQL else "SQLite",
                "connection_test": "failed"
            }

    @staticmethod
    async def check_redis() -> dict:
        """Check Redis connectivity and performance"""
        try:
            start_time = time.time()
            cache_healthy = is_cache_healthy()
            response_time = int((time.time() - start_time) * 1000)

            if cache_healthy:
                # Get memory usage if available
                try:
                    from services.cache_service import get_cache_stats
                    stats = get_cache_stats()
                    memory_mb = stats.get("memory_used_mb", 0)
                except:
                    memory_mb = 0

                return {
                    "healthy": True,
                    "response_time_ms": response_time,
                    "memory_used_mb": memory_mb
                }
            else:
                return {
                    "healthy": False,
                    "response_time_ms": response_time,
                    "error": "Cache service unhealthy"
                }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }

    @staticmethod
    def check_file_system() -> dict:
        """Check file system accessibility"""
        try:
            # Test uploads directory
            test_file = "uploads/health_check_test.txt"
            with open(test_file, "w") as f:
                f.write("health check")
            os.remove(test_file)

            # Get uploads directory size
            uploads_size = 0
            if os.path.exists("uploads"):
                for dirpath, dirnames, filenames in os.walk("uploads"):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        uploads_size += os.path.getsize(filepath)

            return {
                "healthy": True,
                "accessible": True,
                "uploads_size_mb": uploads_size / 1024 / 1024
            }

        except Exception as e:
            return {
                "healthy": False,
                "accessible": False,
                "error": str(e)
            }

    @staticmethod
    def check_memory() -> dict:
        """Check system memory usage"""
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            # Consider unhealthy if > 90% memory used
            healthy = memory_percent < 90

            return {
                "healthy": healthy,
                "total_mb": memory.total / 1024 / 1024,
                "available_mb": memory.available / 1024 / 1024,
                "percent_used": memory_percent,
                "status": "degraded" if memory_percent > 80 else "healthy"
            }

        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
```

## 📊 Application Monitoring

### Key Performance Indicators (KPIs)

**Response Time Metrics:**
- **P50**: Median response time
- **P95**: 95th percentile response time
- **P99**: 99th percentile response time

**Error Rate Metrics:**
- **4xx Errors**: Client errors (bad requests, unauthorized)
- **5xx Errors**: Server errors (internal errors, timeouts)

**Throughput Metrics:**
- **Requests per Second**: Total request rate
- **Concurrent Users**: Active users at any time

### Monitoring Endpoints

**Cache Statistics:**
```http
GET /cache-stats
```

**Response:**
```json
{
  "cache_stats": {
    "hits": 15420,
    "misses": 3840,
    "hit_rate_percent": 80.1,
    "memory_used_mb": 45.2,
    "keys_count": 1250,
    "uptime_days": 7
  }
}
```

**Database Pool Status:**
```http
GET /admin/db-pool-status
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "pool_size": 100,
  "checked_in_connections": 85,
  "checked_out_connections": 15,
  "overflow_connections": 0,
  "invalid_connections": 0
}
```

## 🗄️ Database Monitoring

### Database Performance Metrics

**Connection Pool Monitoring:**
```sql
-- PostgreSQL connection monitoring
SELECT
    datname as database,
    usename as username,
    client_addr as client_ip,
    state,
    query_start,
    state_change,
    waiting
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start DESC;
```

**Query Performance:**
```sql
-- Slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

**Table Statistics:**
```sql
-- Table sizes and statistics
SELECT
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Database Health Checks

**Automated Database Checks:**
```python
# Database monitoring service
class DatabaseMonitor:
    @staticmethod
    async def check_connection_pool():
        """Monitor connection pool health"""
        engine = get_database_session().bind
        pool = engine.pool

        pool_status = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid()
        }

        # Alert if pool usage is high
        usage_percent = (pool_status["checked_out"] / pool_status["size"]) * 100
        if usage_percent > 80:
            alert("High database connection pool usage: {usage_percent}%")

        return pool_status

    @staticmethod
    async def check_slow_queries():
        """Identify slow queries"""
        try:
            db = get_database_session()
            result = db.execute(text("""
                SELECT query, mean_time, calls
                FROM pg_stat_statements
                WHERE mean_time > 1000  -- Slower than 1 second
                ORDER BY mean_time DESC
                LIMIT 10
            """))
            slow_queries = result.fetchall()
            db.close()

            if slow_queries:
                alert(f"Found {len(slow_queries)} slow queries")

            return slow_queries

        except Exception as e:
            logger.error(f"Error checking slow queries: {e}")
            return []
```

## ⚡ Performance Monitoring

### Application Performance Metrics

**Response Time Tracking:**
```python
# middleware/performance.py
import time
from starlette.middleware.base import BaseHTTPMiddleware

class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate response time
        process_time = time.time() - start_time

        # Add custom headers
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Response-Time-MS"] = str(int(process_time * 1000))

        # Log slow requests
        if process_time > 2.0:  # Slower than 2 seconds
            logger.warning(
                f"Slow request: {request.method} {request.url} "
                f"took {process_time:.2f}s"
            )

        return response
```

**Memory Usage Monitoring:**
```python
# services/monitoring_service.py
import psutil
import os

class MonitoringService:
    @staticmethod
    def get_memory_metrics() -> dict:
        """Get detailed memory metrics"""
        process = psutil.Process(os.getpid())

        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,      # Resident Set Size
            "vms_mb": memory_info.vms / 1024 / 1024,      # Virtual Memory Size
            "memory_percent": memory_percent,
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
            "open_files": len(process.open_files())
        }

    @staticmethod
    def get_system_metrics() -> dict:
        """Get system-wide metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "network": psutil.net_io_counters()._asdict()
        }
```

## 🔒 Security Monitoring

### Security Event Monitoring

**Failed Authentication Tracking:**
```python
# services/security_monitor.py
class SecurityMonitor:
    @staticmethod
    def track_failed_login(ip_address: str, username: str):
        """Track failed login attempts"""
        cache_key = f"failed_login:{ip_address}"

        # Increment counter
        failed_count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, failed_count, expire=3600)  # 1 hour

        # Alert if too many failures
        if failed_count > 10:
            alert(f"Multiple failed login attempts from {ip_address}")

        return failed_count

    @staticmethod
    def track_suspicious_activity(activity_type: str, details: dict):
        """Track suspicious activities"""
        security_logger.warning(f"Suspicious activity: {activity_type}", extra=details)

        # Check for patterns
        if activity_type == "sql_injection_attempt":
            SecurityMonitor.block_ip(details.get("ip_address"))

    @staticmethod
    def block_ip(ip_address: str, duration_minutes: int = 60):
        """Block IP address temporarily"""
        cache_key = f"blocked_ip:{ip_address}"
        cache.set(cache_key, True, expire=duration_minutes * 60)

        logger.warning(f"IP {ip_address} blocked for {duration_minutes} minutes")
```

**Rate Limit Violation Tracking:**
```python
# Track rate limit violations
@app.middleware("http")
async def security_monitoring(request, call_next):
    # Check if IP is blocked
    client_ip = get_client_ip(request)
    if cache.get(f"blocked_ip:{client_ip}"):
        return JSONResponse(
            status_code=429,
            content={"error": "IP address is blocked"}
        )

    response = await call_next(request)

    # Track 4xx errors for security monitoring
    if response.status_code >= 400:
        SecurityMonitor.track_error_response(
            client_ip,
            request.method,
            request.url.path,
            response.status_code
        )

    return response
```

## 📈 Business Metrics

### Key Business Metrics

**User Engagement:**
- Daily/Monthly active users
- User registration rate
- User retention rate
- Social connections (follows)

**Event Management:**
- Events created per day
- Event attendance rate
- Event categories popularity
- Geographic distribution

**Financial Metrics:**
- Payment success rate
- Average transaction value
- Revenue per event
- Refund rate

**System Usage:**
- API endpoint usage
- Feature adoption rates
- Error rates by feature
- Performance by endpoint

### Metrics Collection

**Business Metrics Service:**
```python
# services/metrics_service.py
class MetricsService:
    @staticmethod
    async def collect_user_metrics() -> dict:
        """Collect user-related metrics"""
        from utils.database import read_users

        users = read_users()
        total_users = len(users)

        # Calculate active users (users with recent activity)
        active_users = len([
            user for user in users
            if self.is_user_active(user)
        ])

        # User growth rate
        new_users_today = len([
            user for user in users
            if self.is_created_today(user)
        ])

        return {
            "total_users": total_users,
            "active_users": active_users,
            "new_users_today": new_users_today,
            "growth_rate": (new_users_today / total_users) * 100 if total_users > 0 else 0
        }

    @staticmethod
    async def collect_event_metrics() -> dict:
        """Collect event-related metrics"""
        from utils.database import read_events

        events = read_events()
        total_events = len(events)

        # Active events (upcoming)
        active_events = len([
            event for event in events
            if self.is_event_active(event)
        ])

        # Events by category
        category_stats = {}
        for event in events:
            category = event.get("event_type", "unknown")
            category_stats[category] = category_stats.get(category, 0) + 1

        return {
            "total_events": total_events,
            "active_events": active_events,
            "category_distribution": category_stats
        }

    @staticmethod
    async def collect_payment_metrics() -> dict:
        """Collect payment-related metrics"""
        # This would integrate with your payment records
        return {
            "total_payments": 0,
            "successful_payments": 0,
            "failed_payments": 0,
            "total_revenue": 0.0,
            "average_transaction": 0.0
        }
```

## 🚨 Alert Configuration

### Alert Types and Thresholds

**Critical Alerts:**
```python
ALERT_CONFIG = {
    "critical": {
        "health_check_failures": {
            "threshold": 3,
            "window_minutes": 5,
            "severity": "critical"
        },
        "database_unavailable": {
            "threshold": 1,
            "window_minutes": 1,
            "severity": "critical"
        },
        "payment_failure_rate": {
            "threshold": 10,  # 10% failure rate
            "window_minutes": 15,
            "severity": "critical"
        }
    },
    "warning": {
        "high_response_time": {
            "threshold": 2000,  # 2 seconds
            "window_minutes": 5,
            "severity": "warning"
        },
        "high_memory_usage": {
            "threshold": 80,  # 80% memory usage
            "window_minutes": 10,
            "severity": "warning"
        },
        "high_error_rate": {
            "threshold": 5,  # 5% error rate
            "window_minutes": 10,
            "severity": "warning"
        }
    }
}
```

### Alert Implementation

**Alert Service:**
```python
# services/alert_service.py
import requests
import json

class AlertService:
    @staticmethod
    def send_alert(title: str, message: str, severity: str = "info"):
        """Send alert via multiple channels"""

        # Console alert (development)
        if ENVIRONMENT == "development":
            print(f"🚨 ALERT [{severity.upper()}]: {title}")
            print(f"   {message}")

        # Slack notification (production)
        if ENVIRONMENT == "production":
            AlertService.send_slack_alert(title, message, severity)

        # Email notification (critical alerts)
        if severity == "critical":
            AlertService.send_email_alert(title, message)

        # Log alert
        logger.critical(f"ALERT [{severity}]: {title} - {message}")

    @staticmethod
    def send_slack_alert(title: str, message: str, severity: str):
        """Send alert to Slack"""
        slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

        if not slack_webhook:
            return

        color = {
            "critical": "#FF0000",
            "warning": "#FFA500",
            "info": "#0000FF"
        }.get(severity, "#000000")

        payload = {
            "attachments": [{
                "color": color,
                "title": title,
                "text": message,
                "ts": int(time.time())
            }]
        }

        try:
            response = requests.post(slack_webhook, json=payload)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    @staticmethod
    def send_email_alert(title: str, message: str):
        """Send critical alert via email"""
        # Implementation would use your email service
        # e.g., SendGrid, AWS SES, etc.
        pass
```

## 📊 Dashboard Setup

### Metrics Dashboard

**Grafana Dashboard Configuration:**
```json
{
  "dashboard": {
    "title": "Fitness Event Booking Platform",
    "panels": [
      {
        "title": "Response Times",
        "type": "graph",
        "targets": [
          {
            "expr": "response_time_seconds",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(error_total[5m]) * 100"
          }
        ]
      },
      {
        "title": "Active Users",
        "type": "graph",
        "targets": [
          {
            "expr": "active_users"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "db_connections_checked_out"
          }
        ]
      }
    ]
  }
}
```

### Real-time Monitoring

**WebSocket Monitoring:**
```python
# Real-time metrics via WebSocket
@app.websocket("/ws/metrics")
async def metrics_websocket(websocket: WebSocket):
    await websocket.accept()

    while True:
        try:
            # Collect current metrics
            metrics = {
                "timestamp": datetime.now(IST).isoformat(),
                "active_connections": len(manager.active_connections),
                "memory_usage": MonitoringService.get_memory_metrics(),
                "response_times": get_recent_response_times(),
                "error_count": get_recent_error_count()
            }

            await websocket.send_json(metrics)
            await asyncio.sleep(5)  # Update every 5 seconds

        except Exception as e:
            logger.error(f"WebSocket metrics error: {e}")
            break
```

## 📝 Log Management

### Structured Logging

**Application Logs:**
```python
# Structured log format
import json
import logging

class StructuredLogger:
    @staticmethod
    def log_request(request, response, duration):
        """Log API request with structured data"""
        log_data = {
            "event": "api_request",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": int(duration * 1000),
            "client_ip": get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.now(IST).isoformat()
        }

        logger.info(json.dumps(log_data))

    @staticmethod
    def log_business_event(event_type: str, details: dict):
        """Log business events"""
        log_data = {
            "event": event_type,
            "details": details,
            "timestamp": datetime.now(IST).isoformat()
        }

        logger.info(json.dumps(log_data))
```

**Log Aggregation:**
```python
# services/log_service.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Setup structured logging"""

    # Main application logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(getattr(logging, LOG_LEVEL))

    # Rotating file handler
    handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )

    # Structured formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)

    # Security logger
    security_logger = logging.getLogger("security")
    security_handler = RotatingFileHandler(
        "logs/security.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=10
    )
    security_logger.addHandler(security_handler)

    return app_logger, security_logger
```

## 🚨 Incident Response

### Automated Incident Detection

**Incident Detection Rules:**
```python
# services/incident_service.py
class IncidentService:
    @staticmethod
    async def detect_incidents():
        """Detect and respond to incidents"""

        # Check for database issues
        db_health = await HealthService.check_database()
        if not db_health["healthy"]:
            IncidentService.create_incident(
                "database_down",
                "critical",
                f"Database connection failed: {db_health.get('error')}"
            )

        # Check for high error rates
        error_rate = await MetricsService.get_error_rate()
        if error_rate > 10:  # 10% error rate
            IncidentService.create_incident(
                "high_error_rate",
                "warning",
                f"Error rate is {error_rate:.2f}%"
            )

        # Check for performance degradation
        avg_response_time = await MetricsService.get_average_response_time()
        if avg_response_time > 2000:  # 2 seconds
            IncidentService.create_incident(
                "performance_degradation",
                "warning",
                f"Average response time is {avg_response_time}ms"
            )

    @staticmethod
    def create_incident(incident_type: str, severity: str, description: str):
        """Create incident record"""
        incident = {
            "id": str(uuid.uuid4()),
            "type": incident_type,
            "severity": severity,
            "description": description,
            "timestamp": datetime.now(IST).isoformat(),
            "status": "open"
        }

        # Send alert
        AlertService.send_alert(
            f"Incident: {incident_type}",
            description,
            severity
        )

        # Log incident
        logger.critical(f"INCIDENT: {json.dumps(incident)}")

        return incident
```

### Incident Response Procedures

**Automated Response Actions:**
```python
class AutomatedResponse:
    @staticmethod
    async def handle_database_incident(incident):
        """Handle database connectivity issues"""
        # Attempt to restart database connections
        try:
            # Clear connection pool
            engine = get_database_session().bind
            engine.dispose()

            # Wait and test
            await asyncio.sleep(10)

            # Check if resolved
            db_health = await HealthService.check_database()
            if db_health["healthy"]:
                IncidentService.resolve_incident(incident["id"])
                AlertService.send_alert(
                    "Database incident resolved",
                    "Database connectivity restored",
                    "info"
                )

        except Exception as e:
            logger.error(f"Failed to handle database incident: {e}")

    @staticmethod
    async def handle_performance_incident(incident):
        """Handle performance degradation"""
        # Scale up resources if possible
        # Clear caches
        # Restart workers if needed

        AlertService.send_alert(
            "Performance incident response",
            "Applied performance optimization measures",
            "info"
        )
```

## 📊 Metrics Collection

### Prometheus Metrics

**Prometheus Configuration:**
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Business metrics
ACTIVE_USERS = Gauge('active_users', 'Number of active users')
EVENT_COUNT = Gauge('events_total', 'Total number of events')
PAYMENT_COUNT = Counter('payments_total', 'Total payments processed')

# System metrics
MEMORY_USAGE = Gauge('memory_usage_mb', 'Memory usage in MB')
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage')
DB_CONNECTIONS = Gauge('db_connections_active', 'Active database connections')
```

**Metrics Middleware:**
```python
@app.middleware("http")
async def metrics_middleware(request, call_next):
    # Track request metrics
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    REQUEST_COUNT.labels(
        request.method,
        request.url.path,
        response.status_code
    ).inc()

    REQUEST_DURATION.labels(
        request.method,
        request.url.path
    ).observe(duration)

    return response
```

## 🔧 Monitoring Tools Integration

### Monitoring Stack

**Recommended Tools:**
- **Metrics Collection**: Prometheus
- **Visualization**: Grafana
- **Alerting**: Alertmanager
- **Log Aggregation**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **APM**: Jaeger (for distributed tracing)

**Docker Compose Monitoring:**
```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.15.0
    environment:
      - discovery.type=single-node

  logstash:
    image: docker.elastic.co/logstash/logstash:7.15.0
    volumes:
      - ./monitoring/logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: docker.elastic.co/kibana/kibana:7.15.0
    ports:
      - "5601:5601"
```

## 📋 Monitoring Checklist

### Daily Monitoring Tasks

- [ ] Review health check status
- [ ] Check error rates and patterns
- [ ] Monitor response times
- [ ] Review security events
- [ ] Check resource utilization
- [ ] Verify backup status

### Weekly Monitoring Tasks

- [ ] Review performance trends
- [ ] Analyze user engagement metrics
- [ ] Check database performance
- [ ] Review payment success rates
- [ ] Monitor external service dependencies
- [ ] Update monitoring dashboards

### Monthly Monitoring Tasks

- [ ] Security audit review
- [ ] Performance optimization review
- [ ] Capacity planning analysis
- [ ] Incident review and lessons learned
- [ ] Monitoring system updates
- [ ] Alert threshold tuning

## 📞 Emergency Monitoring

### Emergency Dashboard

**Critical Metrics Dashboard:**
```python
@app.get("/emergency/status")
async def emergency_status():
    """Emergency status for critical situations"""
    return {
        "status": "emergency" if critical_issues_detected() else "normal",
        "critical_issues": get_critical_issues(),
        "response_times": get_recent_response_times(),
        "error_rates": get_recent_error_rates(),
        "system_health": await HealthService.comprehensive_health_check(),
        "last_updated": datetime.now(IST).isoformat()
    }
```

### Emergency Contacts

**Emergency Response Team:**
- **Primary**: +91-9876543210 (Tech Lead)
- **Secondary**: +91-9876543211 (DevOps)
- **Tertiary**: +91-9876543212 (Database Admin)

**Emergency Procedures:**
1. Check emergency status endpoint
2. Review critical issues list
3. Contact appropriate team member
4. Follow incident response procedures
5. Document resolution steps

---

## 📚 Additional Resources

### Monitoring Tools

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [ELK Stack Guide](https://www.elastic.co/guide/)
- [Jaeger Tracing](https://www.jaegertracing.io/docs/)

### Best Practices

- [Monitoring Best Practices](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Alert Fatigue Prevention](https://grafana.com/blog/2019/10/31/alerting-best-practices/)
- [Log Management Guide](https://logz.io/blog/log-management-best-practices/)

---

*Last Updated: January 2025*
*Monitoring Version: v2.0.0*
