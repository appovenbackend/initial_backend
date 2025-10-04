# Troubleshooting Guide

## 📋 Table of Contents

1. [Common Issues](#common-issues)
2. [Database Problems](#database-problems)
3. [Authentication Issues](#authentication-issues)
4. [Payment Problems](#payment-problems)
5. [Performance Issues](#performance-issues)
6. [Deployment Issues](#deployment-issues)
7. [Logging and Monitoring](#logging-and-monitoring)
8. [Debug Mode](#debug-mode)
9. [Emergency Procedures](#emergency-procedures)
10. [Getting Help](#getting-help)

## 🚨 Common Issues

### Application Won't Start

**Symptoms:**
- Server fails to start
- Port binding errors
- Import errors

**Troubleshooting Steps:**

1. **Check Python Version:**
```bash
python --version
# Should be Python 3.8 or higher
```

2. **Verify Dependencies:**
```bash
pip list | grep -E "(fastapi|uvicorn|sqlalchemy)"
# Ensure all required packages are installed
```

3. **Check Port Availability:**
```bash
# Linux/Mac
netstat -tulpn | grep :8000

# Windows
netstat -ano | findstr :8000

# Kill process if needed
kill -9 $(lsof -ti:8000)
```

4. **Environment Variables:**
```bash
# Check if .env file exists and is readable
ls -la .env
cat .env | head -5

# Verify critical variables
echo $DATABASE_URL
echo $JWT_SECRET
```

### Import Errors

**Common Import Issues:**

1. **Missing Dependency:**
```bash
pip install missing-package-name
```

2. **Python Path Issues:**
```bash
# Add current directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

3. **Circular Import:**
- Check for circular dependencies in your code
- Move imports inside functions if needed

## 🗄️ Database Problems

### Connection Issues

**PostgreSQL Connection Failed:**

1. **Check Database URL:**
```bash
# Verify format
echo $DATABASE_URL
# Should be: postgresql://user:password@host:port/database
```

2. **Test Connection Manually:**
```bash
# Using psql
psql $DATABASE_URL -c "SELECT 1;"

# Using Python
python -c "
from sqlalchemy import create_engine, text
engine = create_engine('$DATABASE_URL')
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Connection successful')
"
```

3. **Check Database Server:**
```bash
# Railway logs
railway logs

# Local PostgreSQL
sudo systemctl status postgresql
sudo netstat -tulpn | grep 5432
```

**SQLite Issues:**

1. **File Permissions:**
```bash
ls -la data/app.db
chmod 666 data/app.db
```

2. **Directory Exists:**
```bash
mkdir -p data
```

### Migration Issues

**Migration Fails:**

1. **Check Database State:**
```bash
# Check current migration version
alembic current

# Check migration history
alembic history
```

2. **Manual Migration Steps:**
```bash
# Generate new migration
alembic revision --autogenerate -m "fix_issue"

# Apply single migration
alembic upgrade +1

# Rollback if needed
alembic downgrade -1
```

3. **Reset Database (Development Only):**
```bash
# WARNING: This will delete all data
rm -f data/app.db
python migrate_db.py
```

### Connection Pool Issues

**Pool Exhaustion:**

1. **Check Pool Status:**
```python
# Add to your application temporarily
@app.get("/debug/pool-status")
async def get_pool_status():
    engine = get_database_session().bind
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "invalid": pool.invalid()
    }
```

2. **Adjust Pool Settings:**
```python
# core/config.py
DB_POOL_SIZE = 50      # Reduce if too high
DB_MAX_OVERFLOW = 100  # Reduce if too high
DB_POOL_RECYCLE = 3600 # Recycle connections hourly
```

## 🔐 Authentication Issues

### JWT Token Problems

**Token Verification Fails:**

1. **Check JWT Secret:**
```bash
# Ensure JWT_SECRET is consistent
echo $JWT_SECRET
# Should be same across deployments
```

2. **Token Format:**
```bash
# Check token structure
python -c "
import jwt
token = 'your-token-here'
try:
    decoded = jwt.decode(token, 'your-secret', algorithms=['HS256'])
    print('Token valid')
except Exception as e:
    print(f'Token invalid: {e}')
"
```

3. **Token Expiration:**
```python
# Check if token expired
import jwt
import time

token = 'your-token-here'
try:
    decoded = jwt.decode(token, 'your-secret', algorithms=['HS256'])
    exp_time = decoded['exp']
    current_time = time.time()
    if current_time > exp_time:
        print('Token expired')
    else:
        print('Token still valid')
except Exception as e:
    print(f'Token error: {e}')
```

### OAuth Issues

**Google OAuth Fails:**

1. **Check OAuth Configuration:**
```bash
echo $GOOGLE_CLIENT_ID
echo $GOOGLE_CLIENT_SECRET
# Should not be empty
```

2. **OAuth Redirect URI:**
```bash
# Ensure redirect URI matches Google Console
# Should be: https://yourdomain.com/auth/google_login/callback
```

3. **Google Cloud Console:**
- Verify OAuth consent screen is configured
- Check authorized redirect URIs
- Ensure Google+ API is enabled

### OTP Issues

**SMS Not Sending:**

1. **Check SMS Service:**
```python
# Test SMS service integration
python -c "
from services.sms_service import send_sms
result = send_sms('+919876543210', 'Test OTP: 123456')
print(result)
"
```

2. **Phone Number Format:**
```python
# Ensure proper format
phone = '+919876543210'  # Should include country code
```

## 💳 Payment Problems

### Razorpay Integration Issues

**Payment Gateway Errors:**

1. **Check API Keys:**
```bash
# Verify keys are for correct environment
echo $RAZORPAY_KEY_ID
# Should start with rzp_live_ for production
# Should start with rzp_test_ for test
```

2. **Test Payment Creation:**
```python
# Test payment order creation
python -c "
import razorpay
client = razorpay.Client(
    auth=('your_key_id', 'your_key_secret')
)
try:
    order = client.order.create({
        'amount': 50000,  # 500 INR in paisa
        'currency': 'INR'
    })
    print('Payment creation successful')
except Exception as e:
    print(f'Payment error: {e}')
"
```

3. **Webhook Verification:**
```python
# Test webhook signature verification
python -c "
import hmac
import hashlib

webhook_secret = 'your_webhook_secret'
payload = 'your_webhook_payload'
signature = 'webhook_signature'

expected_signature = hmac.new(
    webhook_secret.encode(),
    payload.encode(),
    hashlib.sha256
).hexdigest()

if hmac.compare_digest(f'sha256={expected_signature}', signature):
    print('Valid signature')
else:
    print('Invalid signature')
"
```

## ⚡ Performance Issues

### Slow Response Times

**Database Query Optimization:**

1. **Check Slow Queries:**
```sql
-- PostgreSQL slow query log
SELECT * FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check for missing indexes
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public';
```

2. **Add Missing Indexes:**
```sql
-- Common performance indexes
CREATE INDEX idx_events_start_time ON events (start_time);
CREATE INDEX idx_events_location ON events (location);
CREATE INDEX idx_tickets_event_id ON tickets (event_id);
CREATE INDEX idx_tickets_status ON tickets (status);
```

3. **Query Optimization:**
```python
# Check query execution plan
EXPLAIN ANALYZE
SELECT e.*, u.name
FROM events e
JOIN users u ON e.organizer_id = u.id
WHERE e.start_time > NOW();
```

### Memory Issues

**High Memory Usage:**

1. **Check Memory Usage:**
```bash
# Linux
free -h
ps aux --sort=-%mem | head -10

# Application memory
python -c "
import psutil
process = psutil.Process()
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

2. **Memory Leak Detection:**
```python
# Monitor memory over time
import time
import psutil

def monitor_memory(duration=60):
    process = psutil.Process()
    initial_memory = process.memory_info().rss

    for i in range(duration):
        time.sleep(1)
        current_memory = process.memory_info().rss
        print(f'Memory: {(current_memory - initial_memory) / 1024 / 1024:.2f} MB increase')

monitor_memory()
```

### Cache Issues

**Redis Problems:**

1. **Check Redis Connection:**
```bash
# Test Redis connectivity
redis-cli ping

# Check Redis info
redis-cli info memory
redis-cli info clients
```

2. **Clear Cache if Needed:**
```python
# Clear all cache
python -c "
from services.cache_service import clear_cache_pattern
cleared = clear_cache_pattern('*')
print(f'Cleared {cleared} cache entries')
"
```

## 🚢 Deployment Issues

### Railway Deployment Problems

**Build Fails:**

1. **Check Build Logs:**
```bash
railway logs --build
```

2. **Common Build Issues:**
- Missing dependencies in requirements.txt
- Python version mismatch
- Environment variable issues

**Runtime Errors:**

1. **Check Application Logs:**
```bash
railway logs
```

2. **Environment Variables:**
```bash
# Check if variables are set in Railway
railway variables

# Set missing variables
railway variables set JWT_SECRET=your-secret
```

### Docker Issues

**Container Won't Start:**

1. **Check Docker Logs:**
```bash
docker logs container_name
```

2. **Common Docker Issues:**
- Port conflicts
- Environment variables not passed
- Volume mount issues

**Multi-stage Build Issues:**

1. **Check Build Process:**
```bash
docker build --no-cache -t fitness-app .
```

2. **Debug Build Stages:**
```bash
# Build with target
docker build --target builder -t fitness-app:builder .
```

## 📝 Logging and Monitoring

### Log Analysis

**Application Logs:**

1. **Check Log Files:**
```bash
# Application logs
tail -f app.log

# Security logs
tail -f security.log

# Access logs (if using gunicorn)
tail -f access.log
```

2. **Log Rotation:**
```bash
# Check logrotate status
sudo logrotate -f /etc/logrotate.d/fitness-app

# Check log file sizes
du -sh logs/*.log
```

**Structured Logging:**

1. **Parse JSON Logs:**
```bash
# Convert JSON logs to readable format
tail -f app.log | python -m json.tool
```

2. **Filter Logs:**
```bash
# Filter by log level
tail -f app.log | grep -i error

# Filter by endpoint
tail -f access.log | grep "/api/events"
```

### Health Check Issues

**Health Check Fails:**

1. **Manual Health Check:**
```bash
curl -f http://localhost:8000/health
# Should return 200 OK
```

2. **Debug Health Check:**
```python
# Add detailed health check temporarily
@app.get("/health/debug")
async def debug_health():
    return {
        "database": test_db_connection(),
        "redis": test_redis_connection(),
        "file_system": test_file_access(),
        "memory": get_memory_usage()
    }
```

## 🐛 Debug Mode

### Enable Debug Features

**Debug Configuration:**
```python
# core/config.py
DEBUG = True
LOG_LEVEL = "DEBUG"
DEBUG_LOG_QUERIES = True
DEBUG_LOG_REQUESTS = True
```

**Debug Endpoints:**

1. **Database Debug:**
```python
@app.get("/debug/db-connections")
async def debug_db_connections():
    engine = get_database_session().bind
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_out": pool.checkedout()
    }
```

2. **Cache Debug:**
```python
@app.get("/debug/cache-stats")
async def debug_cache_stats():
    from services.cache_service import get_cache_stats
    return get_cache_stats()
```

3. **Memory Debug:**
```python
@app.get("/debug/memory-usage")
async def debug_memory_usage():
    import psutil
    process = psutil.Process()
    memory = process.memory_info()
    return {
        "rss_mb": memory.rss / 1024 / 1024,
        "vms_mb": memory.vms / 1024 / 1024,
        "cpu_percent": process.cpu_percent()
    }
```

### Debug Tools

**Python Debugger:**
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use ipdb for better experience
import ipdb; ipdb.set_trace()
```

**Request Debugging:**
```python
# Log all incoming requests
@app.middleware("http")
async def debug_requests(request, call_next):
    print(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"Response: {response.status_code}")
    return response
```

## 🚨 Emergency Procedures

### Service Outage

**Step 1: Assess the Situation**
- Check health endpoint: `GET /health`
- Review recent logs for errors
- Check system resources (CPU, memory, disk)

**Step 2: Isolate the Problem**
- Database connection issues?
- External service failures?
- Application code errors?
- Infrastructure problems?

**Step 3: Implement Fix**
- Restart application if needed
- Clear cache if corrupted
- Rollback recent changes if necessary

**Step 4: Verify Resolution**
- Health check passes
- Core functionality works
- No errors in logs

### Data Recovery

**Database Recovery:**

1. **From Backup:**
```bash
# Restore from backup
psql $DATABASE_URL < backup_file.sql

# Verify data integrity
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
```

2. **Point-in-Time Recovery:**
```bash
# If using continuous archiving
psql $DATABASE_URL -c "SELECT pg_wal_replay_resume();"
```

**File System Recovery:**

1. **Restore Uploads:**
```bash
# Extract from backup
tar -xzf uploads_backup_$(date +%Y%m%d).tar.gz -C /app/uploads/
```

2. **Check File Permissions:**
```bash
chmod -R 755 uploads/
chown -R app:app uploads/
```

## 📞 Getting Help

### Support Channels

**1. Check Documentation First**
- Review this troubleshooting guide
- Check the deployment guide
- Review configuration documentation

**2. Application Logs**
- Check `app.log` for application errors
- Check `security.log` for security events
- Check `access.log` for request patterns

**3. System Monitoring**
- Railway dashboard for hosted services
- Docker stats for containerized deployments
- System resource monitoring

### Emergency Contacts

**Technical Support:**
- **Email**: tech-support@yourcompany.com
- **Slack**: #tech-support
- **Phone**: +91-9876543210 (24/7 emergency)

**Development Team:**
- **Lead Developer**: dev-lead@yourcompany.com
- **DevOps Engineer**: devops@yourcompany.com
- **Database Admin**: dba@yourcompany.com

### Reporting Issues

**Bug Report Template:**
```markdown
## Issue Description
[Brief description of the problem]

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- Environment: [development/staging/production]
- Version: [application version]
- Database: [PostgreSQL/SQLite version]
- Python: [Python version]

## Logs
[Relevant log entries]

## Additional Information
[Any other relevant details]
```

## 🔧 Quick Fixes

### Common Quick Fixes

**1. Restart Application:**
```bash
# Development
python main.py

# Production (systemd)
sudo systemctl restart fitness-app

# Docker
docker restart container_name
```

**2. Clear Application Cache:**
```bash
# Clear Redis cache
python -c "
from services.cache_service import clear_cache_pattern
print(f'Cleared {clear_cache_pattern(\"*\")} entries')
"
```

**3. Database Connection Reset:**
```bash
# Test and reset connection
python -c "
from utils.database import get_database_session
db = get_database_session()
db.execute('SELECT 1')
db.close()
print('Database connection OK')
"
```

**4. Check External Services:**
```bash
# Test Razorpay API
curl -H 'Content-Type: application/json' \
     -u 'your_key_id:your_key_secret' \
     https://api.razorpay.com/v1/orders \
     -d '{"amount": 100, "currency": "INR"}'

# Test Redis
redis-cli ping
```

## 📊 Monitoring Dashboard

### Key Metrics to Monitor

**Application Health:**
- Response times (P50, P95, P99)
- Error rates (4xx, 5xx)
- Throughput (requests per second)
- Active connections

**Database Health:**
- Connection pool usage
- Query performance
- Connection errors
- Storage usage

**System Health:**
- CPU usage
- Memory usage
- Disk I/O
- Network I/O

**Business Metrics:**
- User registrations
- Event creation
- Ticket bookings
- Payment success rate

### Alert Thresholds

**Critical Alerts:**
- Health check fails for > 5 minutes
- Error rate > 10%
- Database connection pool exhausted
- Payment failure rate > 5%

**Warning Alerts:**
- Response time > 2 seconds
- Memory usage > 80%
- Cache hit rate < 70%
- Failed login attempts > 100/hour

## 🔍 Diagnostic Commands

### System Diagnostics

**Complete System Check:**
```bash
#!/bin/bash
# diagnostic.sh

echo "=== System Diagnostics ==="
echo "Date: $(date)"
echo "Uptime: $(uptime)"

echo -e "\n=== Memory Usage ==="
free -h

echo -e "\n=== Disk Usage ==="
df -h

echo -e "\n=== Active Processes ==="
ps aux --sort=-%cpu | head -10

echo -e "\n=== Network Connections ==="
netstat -tulpn | grep :8000

echo -e "\n=== Application Logs (Last 10 lines) ==="
tail -10 app.log

echo -e "\n=== Health Check ==="
curl -f http://localhost:8000/health || echo "Health check failed"
```

### Database Diagnostics

**Database Health Check:**
```sql
-- Comprehensive database health check
SELECT
    'users' as table_name,
    COUNT(*) as record_count,
    pg_size_pretty(pg_total_relation_size('users')) as size
FROM users
UNION ALL
SELECT
    'events' as table_name,
    COUNT(*) as record_count,
    pg_size_pretty(pg_total_relation_size('events')) as size
FROM events
UNION ALL
SELECT
    'tickets' as table_name,
    COUNT(*) as record_count,
    pg_size_pretty(pg_total_relation_size('tickets')) as size
FROM tickets;
```

### Performance Diagnostics

**Slow Query Detection:**
```sql
-- Find slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
WHERE mean_time > 100  -- Queries slower than 100ms
ORDER BY mean_time DESC
LIMIT 10;
```

## 📚 Additional Resources

### Useful Tools

- **PostgreSQL Tools**: pgAdmin, psql, pg_stat_statements
- **Redis Tools**: redis-cli, Redis Insight
- **Network Tools**: curl, netstat, tcpdump
- **Performance Tools**: htop, psutil, memory_profiler
- **Log Analysis**: grep, awk, jq

### Learning Resources

- [FastAPI Troubleshooting](https://fastapi.tiangolo.com/tutorial/debugging/)
- [PostgreSQL Performance](https://postgresql.org/docs/current/performance-tips.html)
- [Redis Administration](https://redis.io/topics/admin)
- [Python Debugging](https://docs.python.org/3/library/pdb.html)

---

## 🎯 Prevention

### Best Practices to Avoid Issues

1. **Regular Monitoring**: Set up alerts for key metrics
2. **Log Analysis**: Regular review of application logs
3. **Performance Testing**: Load test before deployment
4. **Backup Verification**: Test backup restoration regularly
5. **Configuration Management**: Use version control for config
6. **Documentation**: Keep troubleshooting docs updated

### Maintenance Schedule

- **Daily**: Check health endpoints, review error logs
- **Weekly**: Performance analysis, security review
- **Monthly**: Load testing, dependency updates
- **Quarterly**: Security audit, architecture review

---

*Last Updated: January 2025*
*Troubleshooting Version: v2.0.0*
