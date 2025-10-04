# Configuration Guide

## 📋 Table of Contents

1. [Environment Variables](#environment-variables)
2. [Database Configuration](#database-configuration)
3. [Security Configuration](#security-configuration)
4. [Payment Configuration](#payment-configuration)
5. [OAuth Configuration](#oauth-configuration)
6. [Caching Configuration](#caching-configuration)
7. [Performance Tuning](#performance-tuning)
8. [Logging Configuration](#logging-configuration)
9. [File Upload Configuration](#file-upload-configuration)
10. [Development vs Production](#development-vs-production)

## 🌍 Environment Variables

### Required Variables

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` | Production |
| `JWT_SECRET` | JWT token signing secret | `your-secret-key-min-32-chars` | Yes |
| `RAZORPAY_KEY_ID` | Razorpay payment gateway key | `rzp_live_xxx` | Yes |
| `RAZORPAY_KEY_SECRET` | Razorpay secret key | `your-secret` | Yes |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | `your-client-id` | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | `your-client-secret` | Optional |
| `REDIS_URL` | Redis cache URL | `redis://host:port/db` | Optional |

### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENVIRONMENT` | Environment type | `development` | `production` |
| `DEBUG` | Debug mode | `False` | `True` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `PORT` | Server port | `8000` | `8080` |
| `MAX_REQUEST_SIZE` | Max request size | `5242880` | `10485760` |
| `DB_POOL_SIZE` | Database pool size | `100` | `200` |
| `DB_MAX_OVERFLOW` | Max overflow connections | `200` | `400` |

## 🗄️ Database Configuration

### PostgreSQL Configuration

**Production Database URL:**
```bash
DATABASE_URL=postgresql+psycopg2://username:password@hostname:5432/database_name?sslmode=require
```

**Connection Pool Settings:**
```python
# core/config.py
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "100"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "200"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
```

**SQLite Configuration (Development):**
```bash
# No DATABASE_URL needed - automatically uses SQLite
DATABASE_FILE = "data/app.db"
```

### Database Migration

**Alembic Configuration:**
```ini
# alembic.ini
sqlalchemy.url = postgresql://user:pass@host/db

[alembic:exclude]
# Exclude certain tables from autogenerate
tables = temporary_tables,audit_tables
```

## 🔐 Security Configuration

### JWT Configuration

**Token Settings:**
```python
# core/config.py
SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2 hours

# Enhanced JWT security
JWT_KID = os.getenv("JWT_KID", "v1")  # Key ID for rotation
```

**Security Headers:**
```python
# core/config.py
ENABLE_SECURITY_HEADERS = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"
ENABLE_REQUEST_LOGGING = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "5242880"))  # 5MB
```

### Rate Limiting

**Rate Limit Configuration:**
```python
# core/rate_limiting.py
from slowapi import Limiter

# Global rate limiter
limiter = Limiter(key_func=get_remote_address)

# Custom limits per endpoint
AUTH_RATE_LIMIT = "5/minute"
API_RATE_LIMIT = "100/minute"
FILE_UPLOAD_LIMIT = "10/minute"
PAYMENT_LIMIT = "30/minute"
```

## 💳 Payment Configuration

### Razorpay Settings

**Production Configuration:**
```bash
RAZORPAY_KEY_ID=rzp_live_your_production_key_id
RAZORPAY_KEY_SECRET=your_production_secret_key
RAZORPAY_WEBHOOK_SECRET=your_webhook_verification_secret
```

**Test Configuration:**
```bash
RAZORPAY_KEY_ID=rzp_test_your_test_key_id
RAZORPAY_KEY_SECRET=your_test_secret_key
RAZORPAY_WEBHOOK_SECRET=your_test_webhook_secret
```

**Payment Settings:**
```python
# core/config.py
PAYMENT_CURRENCY = "INR"
PAYMENT_TIMEOUT_MINUTES = 10
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")
```

## 🔑 OAuth Configuration

### Google OAuth Setup

**Step 1: Create Google OAuth Application**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs

**Step 2: Configure Environment**
```bash
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**OAuth Scopes:**
```python
# core/config.py
GOOGLE_OAUTH_SCOPES = [
    "openid",
    "email",
    "profile"
]
```

## ⚡ Caching Configuration

### Redis Configuration

**Production Redis:**
```bash
REDIS_URL=redis://username:password@hostname:port/database_number
```

**Development Redis:**
```bash
REDIS_URL=redis://localhost:6379/0
```

**Cache Settings:**
```python
# services/cache_service.py
CACHE_TTL = {
    "user_session": 3600,        # 1 hour
    "event_data": 1800,         # 30 minutes
    "payment_status": 300,      # 5 minutes
    "qr_validation": 900        # 15 minutes
}
```

## 🚀 Performance Tuning

### Gunicorn Configuration

**gunicorn.conf.py:**
```python
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Timeout settings
timeout = 30
keepalive = 2

# Restart policy
preload_app = True
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
```

### Database Performance

**Connection Pool Tuning:**
```python
# Optimal settings for different server sizes
SERVER_SIZES = {
    "small": {
        "pool_size": 20,
        "max_overflow": 40,
        "pool_timeout": 30
    },
    "medium": {
        "pool_size": 100,
        "max_overflow": 200,
        "pool_timeout": 30
    },
    "large": {
        "pool_size": 200,
        "max_overflow": 400,
        "pool_timeout": 60
    }
}
```

## 📝 Logging Configuration

### Application Logging

**Logging Levels:**
```python
# core/config.py
LOG_LEVELS = {
    "development": "DEBUG",
    "staging": "INFO",
    "production": "WARNING"
}

LOG_LEVEL = os.getenv("LOG_LEVEL", LOG_LEVELS.get(ENVIRONMENT, "INFO"))
```

**Log Format:**
```python
import logging

# Structured logging format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# JSON format for production
JSON_LOG_FORMAT = {
    "timestamp": "%(asctime)s",
    "level": "%(levelname)s",
    "logger": "%(name)s",
    "message": "%(message)s",
    "module": "%(module)s",
    "function": "%(funcName)s",
    "line": "%(lineno)d"
}
```

### Security Logging

**Security Events to Log:**
- Authentication failures
- Authorization violations
- Suspicious IP addresses
- SQL injection attempts
- File upload violations
- Payment anomalies

## 📁 File Upload Configuration

### Upload Settings

**File Size Limits:**
```python
# core/config.py
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB general limit

# Specific limits by file type
FILE_SIZE_LIMITS = {
    "image": 5 * 1024 * 1024,      # 5MB for images
    "document": 10 * 1024 * 1024,  # 10MB for documents
    "video": 50 * 1024 * 1024      # 50MB for videos
}
```

**Allowed File Types:**
```python
ALLOWED_EXTENSIONS = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp"},
    "document": {".pdf", ".doc", ".docx", ".txt"},
    "video": {".mp4", ".avi", ".mov"}
}
```

## 🔧 Development vs Production

### Development Configuration

**development.env:**
```bash
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=

# JWT (insecure for development)
JWT_SECRET=dev-secret-key-not-secure

# OAuth (optional for development)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Payments (use test keys)
RAZORPAY_KEY_ID=rzp_test_xxx
RAZORPAY_KEY_SECRET=test_secret

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Security (relaxed for development)
MAX_REQUEST_SIZE=10485760
ENABLE_SECURITY_HEADERS=False
```

### Production Configuration

**production.env:**
```bash
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING

# Database (PostgreSQL required)
DATABASE_URL=postgresql+psycopg2://user:pass@host/db?sslmode=require

# JWT (secure secret required)
JWT_SECRET=your-production-secret-at-least-32-characters-long

# OAuth (required for production)
GOOGLE_CLIENT_ID=your-production-client-id
GOOGLE_CLIENT_SECRET=your-production-client-secret

# Payments (live keys required)
RAZORPAY_KEY_ID=rzp_live_xxx
RAZORPAY_KEY_SECRET=live_secret
RAZORPAY_WEBHOOK_SECRET=webhook_secret

# Redis (required for production)
REDIS_URL=redis://user:pass@host:port/db

# Security (strict for production)
MAX_REQUEST_SIZE=5242880
ENABLE_SECURITY_HEADERS=True
ENABLE_REQUEST_LOGGING=True

# Performance
DB_POOL_SIZE=100
DB_MAX_OVERFLOW=200
```

## ⚙️ Configuration Files

### core/config.py

**Main Configuration File:**
```python
import os
from datetime import timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Basic settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Timezone
IST = timezone(timedelta(hours=5, minutes=30))

# Security
SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey123")
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRESQL = bool(DATABASE_URL)

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Payments
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Performance
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "100"))
MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "5242880"))
```

### gunicorn.conf.py

**Production Server Configuration:**
```python
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Timeout and keepalive
timeout = 30
keepalive = 2

# Restart workers periodically
preload_app = True
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
capture_output = True

# SSL (if needed)
keyfile = os.getenv("SSL_KEY_FILE")
certfile = os.getenv("SSL_CERT_FILE")
```

## 🔍 Configuration Validation

### Configuration Checker

**config_validator.py:**
```python
import os
from typing import List, Dict

class ConfigurationValidator:
    REQUIRED_VARS = [
        "JWT_SECRET",
        "RAZORPAY_KEY_ID",
        "RAZORPAY_KEY_SECRET"
    ]

    PRODUCTION_REQUIRED_VARS = [
        "DATABASE_URL",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "REDIS_URL"
    ]

    @staticmethod
    def validate_config() -> Dict[str, List[str]]:
        """Validate current configuration"""
        errors = []
        warnings = []

        # Check required variables
        for var in ConfigurationValidator.REQUIRED_VARS:
            if not os.getenv(var):
                errors.append(f"Missing required variable: {var}")

        # Check production-specific variables
        if os.getenv("ENVIRONMENT") == "production":
            for var in ConfigurationValidator.PRODUCTION_REQUIRED_VARS:
                if not os.getenv(var):
                    errors.append(f"Missing production variable: {var}")

        # Check JWT secret strength
        jwt_secret = os.getenv("JWT_SECRET")
        if jwt_secret and len(jwt_secret) < 32:
            warnings.append("JWT_SECRET should be at least 32 characters long")

        # Check database URL format
        db_url = os.getenv("DATABASE_URL")
        if db_url and not db_url.startswith(("postgresql://", "postgresql+psycopg2://")):
            warnings.append("DATABASE_URL should use PostgreSQL in production")

        return {
            "errors": errors,
            "warnings": warnings
        }

    @staticmethod
    def print_config_status():
        """Print current configuration status"""
        result = ConfigurationValidator.validate_config()

        if result["errors"]:
            print("❌ Configuration Errors:")
            for error in result["errors"]:
                print(f"  - {error}")

        if result["warnings"]:
            print("⚠️  Configuration Warnings:")
            for warning in result["warnings"]:
                print(f"  - {warning}")

        if not result["errors"] and not result["warnings"]:
            print("✅ Configuration is valid!")

        return len(result["errors"]) == 0
```

**Usage:**
```bash
# Validate configuration
python -c "from config_validator import ConfigurationValidator; ConfigurationValidator.print_config_status()"
```

## 🔄 Configuration Management

### Environment-Specific Files

**.env.development:**
```bash
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=DEBUG
JWT_SECRET=dev-secret-key-for-development-only
```

**.env.production:**
```bash
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING
JWT_SECRET=your-secure-production-secret-key-here
```

### Docker Configuration

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  web:
    image: fitness-app:latest
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
      - RAZORPAY_KEY_ID=${RAZORPAY_KEY_ID}
      - RAZORPAY_KEY_SECRET=${RAZORPAY_KEY_SECRET}
    env_file:
      - .env.production
```

## 📊 Monitoring Configuration

### Health Check Configuration

**Health Check Settings:**
```python
# core/config.py
HEALTH_CHECK_TIMEOUT = 10  # seconds
HEALTH_CHECK_RETRIES = 3
HEALTH_CHECK_INTERVAL = 30  # seconds

# Components to check
HEALTH_CHECKS = {
    "database": True,
    "redis": True,
    "file_system": True,
    "memory": True,
    "external_apis": False  # Disable for faster checks
}
```

### Metrics Configuration

**Metrics to Collect:**
```python
# core/config.py
METRICS_CONFIG = {
    "response_times": True,
    "error_rates": True,
    "database_performance": True,
    "cache_performance": True,
    "payment_metrics": True,
    "security_metrics": True
}
```

## 🚨 Troubleshooting Configuration

### Debug Configuration

**Debug Settings:**
```python
# core/config.py
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
DEBUG_LOG_QUERIES = os.getenv("DEBUG_LOG_QUERIES", "False").lower() == "true"
DEBUG_LOG_REQUESTS = os.getenv("DEBUG_LOG_REQUESTS", "False").lower() == "true"
```

**Enable Debug Features:**
```bash
# Set these for debugging
DEBUG=True
DEBUG_LOG_QUERIES=True
DEBUG_LOG_REQUESTS=True
LOG_LEVEL=DEBUG
```

### Common Configuration Issues

**1. Database Connection Issues:**
```bash
# Check database URL format
echo $DATABASE_URL

# Test database connection
python -c "
import os
from sqlalchemy import create_engine
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print('Database connection successful')
"
```

**2. JWT Secret Issues:**
```bash
# Check JWT secret length
python -c "
import os
secret = os.getenv('JWT_SECRET', '')
print(f'JWT_SECRET length: {len(secret)}')
print('Should be at least 32 characters for security')
"
```

**3. Redis Connection Issues:**
```bash
# Test Redis connection
python -c "
import redis
r = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
try:
    r.ping()
    print('Redis connection successful')
except Exception as e:
    print(f'Redis connection failed: {e}')
"
```

## 📚 Best Practices

### Security Best Practices

1. **Never commit secrets** to version control
2. **Use strong JWT secrets** (minimum 32 characters)
3. **Rotate secrets regularly** in production
4. **Use different secrets** for different environments
5. **Limit variable exposure** in logs and error messages

### Performance Best Practices

1. **Tune connection pools** based on server capacity
2. **Use Redis for caching** in production
3. **Enable gzip compression** for API responses
4. **Monitor resource usage** regularly
5. **Scale horizontally** when needed

### Maintenance Best Practices

1. **Validate configuration** before deployment
2. **Document configuration changes**
3. **Test configuration** in staging environment
4. **Backup configuration files**
5. **Review configuration** regularly for optimization

---

## 📞 Support

For configuration issues:
- Check the troubleshooting section above
- Validate your configuration with the provided validator
- Review application logs for configuration errors
- Ensure all required environment variables are set

---

*Last Updated: January 2025*
*Configuration Version: v2.0.0*
