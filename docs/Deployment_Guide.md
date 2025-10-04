# Deployment Guide

## 📋 Table of Contents

1. [Development Setup](#development-setup)
2. [Production Deployment](#production-deployment)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [Docker Deployment](#docker-deployment)
6. [Railway Deployment](#railway-deployment)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)
9. [Performance Optimization](#performance-optimization)
10. [Troubleshooting](#troubleshooting)

## 🛠️ Development Setup

### Prerequisites

**System Requirements:**
- Python 3.8 or higher
- PostgreSQL (optional, SQLite used by default)
- Redis (optional, for caching)
- Git

**Install Python Dependencies:**
```bash
# Clone the repository
git clone https://github.com/your-org/fitness-event-booking.git
cd fitness-event-booking

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

**Copy Environment Template:**
```bash
cp .env.example .env
```

**Configure Development Environment:**
```bash
# .env file
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# Database (SQLite for development)
DATABASE_URL=

# JWT Configuration
JWT_SECRET=your-development-secret-key-change-this-in-production

# OAuth (Optional for development)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Payment Gateway (Use test keys)
RAZORPAY_KEY_ID=rzp_test_your_test_key
RAZORPAY_KEY_SECRET=your_test_secret

# Redis (Optional)
REDIS_URL=redis://localhost:6379
```

### Database Setup

**Initialize Database:**
```bash
# Run database migrations
python migrate_db.py

# Verify database setup
python -c "from utils.database import get_database_session; print('Database connected successfully')"
```

**Start Development Server:**
```bash
# Start the application
python main.py

# Or use uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Access the Application:**
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## 🚀 Production Deployment

### Production Checklist

- [ ] Domain name and SSL certificate
- [ ] Production database (PostgreSQL)
- [ ] Redis for caching
- [ ] Environment variables configured
- [ ] Secrets management
- [ ] Monitoring and logging
- [ ] Backup strategy
- [ ] Security headers and HTTPS

### Environment Variables

**Required Production Variables:**
```bash
# Application
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING
SECRET_KEY=your-production-secret-key

# Database
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database_name

# JWT
JWT_SECRET=your-super-secret-jwt-key-minimum-32-characters

# OAuth
GOOGLE_CLIENT_ID=your-production-google-client-id
GOOGLE_CLIENT_SECRET=your-production-google-client-secret

# Payment Gateway
RAZORPAY_KEY_ID=rzp_live_your_live_key
RAZORPAY_KEY_SECRET=your_live_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Redis
REDIS_URL=redis://username:password@host:port/database

# Security
MAX_REQUEST_SIZE=5242880
ENABLE_SECURITY_HEADERS=True
ENABLE_REQUEST_LOGGING=True

# Performance
DB_POOL_SIZE=100
DB_MAX_OVERFLOW=200
```

## 🐳 Docker Deployment

### Dockerfile

```dockerfile
# Multi-stage build for optimal image size
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/fitness_app
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - uploads:/app/uploads
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=fitness_app
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
  uploads:
```

**Deploy with Docker:**
```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f web

# Scale the application
docker-compose up -d --scale web=3
```

## 🚂 Railway Deployment

### Railway Configuration

**railway.toml:**
```toml
[build]
builder = "python"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"

[environments.production]
variables = [
    { name = "ENVIRONMENT", value = "production" },
    { name = "DEBUG", value = "False" }
]
```

**Deploy Steps:**
1. **Connect Repository**: Link your GitHub repository to Railway
2. **Configure Variables**: Set all required environment variables
3. **Database Setup**: Railway automatically provides PostgreSQL
4. **Deploy**: Push to main branch or trigger manual deployment

**Railway Environment Variables:**
```bash
# Railway provides these automatically
DATABASE_URL=postgresql://user:password@host:5432/railway

# Set these manually
JWT_SECRET=your-production-secret
RAZORPAY_KEY_ID=rzp_live_your_key
RAZORPAY_KEY_SECRET=your_secret
GOOGLE_CLIENT_ID=your_google_id
GOOGLE_CLIENT_SECRET=your_google_secret
```

## ⚙️ Environment Configuration

### Configuration Files

**core/config.py** - Main application configuration
**alembic.ini** - Database migration settings
**gunicorn.conf.py** - Production server configuration

### Environment-Specific Settings

**Development:**
```python
# core/config.py
DEBUG = True
LOG_LEVEL = "DEBUG"
DATABASE_URL = None  # Use SQLite
REDIS_URL = "redis://localhost:6379"
```

**Production:**
```python
# core/config.py
DEBUG = False
LOG_LEVEL = "WARNING"
DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL
REDIS_URL = os.getenv("REDIS_URL")  # Production Redis
```

## 🗄️ Database Setup

### PostgreSQL Setup

**Railway PostgreSQL:**
Railway automatically provides a PostgreSQL database with:
- Connection pooling
- Automatic backups
- High availability

**Manual PostgreSQL Setup:**
```bash
# Create database
createdb fitness_app

# Create user
createuser --interactive --pwprompt fitness_user

# Grant permissions
GRANT ALL PRIVILEGES ON DATABASE fitness_app TO fitness_user;
```

**Database Migrations:**
```bash
# Run all migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "add_user_preferences"

# Apply specific migration
alembic upgrade +1

# Rollback migration
alembic downgrade -1
```

### Database Connection Pooling

**Configuration:**
```python
# core/config.py
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "100"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "200"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
```

**Connection String:**
```bash
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/db?sslmode=require&pool_size=100&max_overflow=200
```

## 📊 Monitoring & Logging

### Application Monitoring

**Health Check Endpoints:**
```bash
# Comprehensive health check
curl https://your-app.com/health

# Cache statistics
curl https://your-app.com/cache-stats

# Database status
curl https://your-app.com/health | jq '.database'
```

**Key Metrics to Monitor:**
- Response times (P50, P95, P99)
- Error rates (4xx, 5xx)
- Database connection pool usage
- Cache hit rates
- Payment success rates

### Logging Configuration

**Production Logging:**
```python
# main.py
import logging

# Structured logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/app.log'),
        logging.StreamHandler()
    ]
)

# Separate security logging
security_logger = logging.getLogger('security')
security_logger.addHandler(logging.FileHandler('/app/logs/security.log'))
```

**Log Rotation:**
```bash
# Logrotate configuration /etc/logrotate.d/fitness-app
/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 app app
}
```

## 💾 Backup & Recovery

### Database Backup

**Automated Backups (Railway):**
- Daily automatic backups
- Point-in-time recovery
- Cross-region replication

**Manual Backup:**
```bash
# Create backup
pg_dump -h host -U user -d database > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
psql -h host -U user -d database < backup_file.sql
```

**Backup Strategy:**
- **Daily**: Full database backup
- **Hourly**: Transaction log backup
- **Retention**: 30 days of daily backups, 7 days of hourly backups

### File System Backup

**Uploads Directory:**
```bash
# Backup uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz /app/uploads/

# Restore uploads
tar -xzf uploads_backup_file.tar.gz -C /app/
```

## ⚡ Performance Optimization

### Application Performance

**Gunicorn Configuration:**
```python
# gunicorn.conf.py
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers
preload_app = True
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
```

**Redis Caching:**
```python
# services/cache_service.py
import redis
import json
from typing import Any, Optional

class CacheService:
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = self.redis_client.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: Any, expire: int = 3600) -> None:
        """Set value in cache with expiration"""
        self.redis_client.setex(key, expire, json.dumps(value))

    def delete(self, key: str) -> None:
        """Delete key from cache"""
        self.redis_client.delete(key)
```

### Database Performance

**Query Optimization:**
```sql
-- Create composite indexes for common queries
CREATE INDEX idx_events_datetime_location ON events (start_time, location);
CREATE INDEX idx_tickets_event_status ON tickets (event_id, status);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM events WHERE start_time > NOW() AND location = 'Mumbai';
```

**Connection Pool Monitoring:**
```python
# Monitor connection pool
@app.get("/admin/db-pool-status")
async def get_db_pool_status():
    engine = get_database_session().bind
    pool = engine.pool

    return {
        "pool_size": pool.size(),
        "checked_in_connections": pool.checkedin(),
        "checked_out_connections": pool.checkedout(),
        "invalid_connections": pool.invalid()
    }
```

## 🔧 Troubleshooting

### Common Deployment Issues

**1. Database Connection Issues:**
```bash
# Test database connection
python -c "
from sqlalchemy import create_engine, text
engine = create_engine('your_database_url')
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection successful')
"
```

**2. Environment Variables:**
```bash
# Check if variables are loaded
python -c "
import os
print('DATABASE_URL:', os.getenv('DATABASE_URL')[:20] + '...' if os.getenv('DATABASE_URL') else 'Not set')
print('JWT_SECRET:', 'Set' if os.getenv('JWT_SECRET') else 'Not set')
"
```

**3. Port Binding Issues:**
```bash
# Check if port is available
netstat -tulpn | grep :8000

# Kill process using port
kill -9 $(lsof -ti:8000)
```

**4. Memory Issues:**
```bash
# Check memory usage
free -h

# Monitor application memory
ps aux --sort=-%mem | head -10
```

### Debug Mode

**Enable Debug Logging:**
```python
# Set in environment
DEBUG=True
LOG_LEVEL=DEBUG

# Or modify code temporarily
logging.getLogger().setLevel(logging.DEBUG)
```

**Common Debug Commands:**
```bash
# Test all endpoints
curl -f http://localhost:8000/health || echo "Health check failed"

# Check database connectivity
python -c "from utils.database import get_database_session; print('DB OK')"

# Verify Redis connection
python -c "from services.cache_service import get_cache; print('Redis OK')"
```

## 🚨 Production Checklist

### Pre-Deployment
- [ ] All tests pass
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificate installed
- [ ] Domain DNS configured
- [ ] Backup strategy tested

### Post-Deployment
- [ ] Application starts successfully
- [ ] Health check passes
- [ ] Database connection verified
- [ ] External services accessible
- [ ] SSL certificate valid
- [ ] Monitoring alerts configured

### Rollback Plan
- [ ] Database backup available
- [ ] Previous version ready for deployment
- [ ] Rollback script prepared
- [ ] Team notification ready

## 📞 Support

**Emergency Contacts:**
- **Technical Lead**: tech-lead@yourcompany.com
- **DevOps Team**: devops@yourcompany.com
- **Database Admin**: dba@yourcompany.com

**Monitoring Dashboards:**
- Application metrics: https://your-monitoring.com/app
- Database metrics: https://your-monitoring.com/db
- Error tracking: https://your-error-tracker.com

---

## 📚 Additional Resources

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [PostgreSQL Production Setup](https://postgresql.org/docs/current/high-availability.html)
- [Redis Production Guide](https://redis.io/topics/admin)
- [Railway Documentation](https://docs.railway.app)

---

*Last Updated: January 2025*
*Deployment Version: v2.0.0*
