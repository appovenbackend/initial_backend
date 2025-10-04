# Authentication & Security Documentation

## 📋 Table of Contents

1. [Authentication Methods](#authentication-methods)
2. [JWT Token Management](#jwt-token-management)
3. [OAuth Integration](#oauth-integration)
4. [OTP Verification](#otp-verification)
5. [Security Features](#security-features)
6. [Rate Limiting](#rate-limiting)
7. [Input Validation](#input-validation)
8. [Security Headers](#security-headers)
9. [File Upload Security](#file-upload-security)
10. [Audit Logging](#audit-logging)

## 🔐 Authentication Methods

### 1. JWT Token Authentication

**Token Structure:**
```json
{
  "typ": "JWT",
  "alg": "HS256"
}
```

**Payload Claims:**
```json
{
  "user_id": "u_abc123def4",
  "role": "user",
  "iat": 1640995200,
  "exp": 1641002400,
  "iss": "fitness-event-booking",
  "aud": "fitness-app-users"
}
```

**Usage:**
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

### 2. Google OAuth 2.0

**OAuth Flow:**
```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant G as Google

    U->>F: Click "Login with Google"
    F->>B: GET /auth/google_login
    B->>G: Redirect to Google OAuth
    G->>U: OAuth Consent Screen
    U->>G: Grant Permission
    G->>B: Callback with auth code
    B->>G: Exchange code for tokens
    G->>B: Return user profile
    B->>F: Redirect with JWT token
```

**OAuth Configuration:**
```python
# core/config.py
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# OAuth registration in main.py
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
```

### 3. OTP Verification

**OTP Process:**
```mermaid
graph TD
    A[User Request OTP] --> B[Generate 6-digit OTP]
    B --> C[Store OTP with expiry]
    C --> D[Send OTP via SMS]
    D --> E[User enters OTP]
    E --> F[Validate OTP]
    F --> G{Valid?}
    G -->|Yes| H[Authentication Success]
    G -->|No| I[Authentication Failed]
```

**OTP Endpoints:**
- `POST /auth/request-otp` - Request OTP for phone number
- `POST /auth/verify-otp` - Verify OTP and authenticate user

## 🔑 JWT Token Management

### Token Creation

**Enhanced JWT Security Manager:**
```python
# core/jwt_security.py
class JWTSecurityManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(self, user_id: str, metadata: dict) -> str:
        """Create JWT token with enhanced security"""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "user_id": user_id,
            "role": metadata.get("role", "user"),
            "iat": now,
            "exp": expire,
            "iss": "fitness-event-booking",
            "aud": "fitness-app-users",
            "jti": str(uuid.uuid4()),  # Unique token ID
            "type": "access"
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="fitness-app-users",
                issuer="fitness-event-booking"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
```

### Token Storage

**Security Best Practices:**
- Store tokens in HTTP-only cookies for web clients
- Use secure flag in production (HTTPS only)
- Set appropriate expiration times
- Implement token refresh mechanism

## 🛡️ Security Features

### 1. Password Security

**Password Hashing:**
```python
# core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password with salt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)
```

**Password Requirements:**
- Minimum 8 characters
- Mix of uppercase and lowercase letters
- Include numbers and special characters
- Not commonly used passwords

### 2. SQL Injection Protection

**Input Sanitization:**
```python
# utils/security.py
class SQLProtection:
    @staticmethod
    def sanitize_input(data: dict) -> dict:
        """Sanitize user input to prevent SQL injection"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Remove potentially dangerous characters
                sanitized[key] = value.replace("'", "''").replace(";", "")
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        import re
        pattern = r'^\+?[1-9]\d{1,14}$'
        return re.match(pattern, phone) is not None
```

### 3. XSS Protection

**Input Validation:**
```python
# utils/security.py
class XSSProtection:
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Remove potentially dangerous HTML/script content"""
        import html
        return html.escape(text)

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        import re
        pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?$'
        return re.match(pattern, url) is not None
```

## 🚦 Rate Limiting

### Implementation

**SlowAPI Configuration:**
```python
# core/rate_limiting.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Custom rate limit decorators
def api_rate_limit(limit_value: str):
    def decorator(func):
        return limiter.limit(limit_value)(func)
    return decorator

def auth_rate_limit(limit_value: str):
    def decorator(func):
        return limiter.limit(limit_value, per_method=True)(func)
    return decorator
```

### Rate Limit Categories

| Endpoint Type | Limit | Window | Purpose |
|---------------|-------|--------|---------|
| **Authentication** | 5-10 req/min | 15 minutes | Prevent brute force |
| **General API** | 100 req/min | 1 minute | General protection |
| **File Upload** | 10 req/min | 5 minutes | Resource protection |
| **Payment** | 30 req/min | 1 minute | Fraud prevention |
| **Admin** | 50 req/min | 1 minute | Administrative access |

### Rate Limit Response

```json
{
  "error": "Rate limit exceeded",
  "detail": "Too many requests",
  "retry_after": 300,
  "status_code": 429,
  "limit": "100/minute",
  "remaining": 0,
  "reset_time": "2025-01-04T16:23:51+05:30"
}
```

## 🔒 Security Headers

### Security Headers Middleware

```python
# middleware/security.py
class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    [b"x-content-type-options", b"nosniff"],
                    [b"x-frame-options", b"DENY"],
                    [b"x-xss-protection", b"1; mode=block"],
                    [b"strict-transport-security", b"max-age=31536000; includeSubDomains"],
                    [b"referrer-policy", b"strict-origin-when-cross-origin"],
                    [b"permissions-policy", b"geolocation=(), microphone=(), camera=()"],
                    [b"content-security-policy", b"default-src 'self'"],
                ])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
```

### Security Headers Explained

| Header | Purpose | Value |
|--------|---------|-------|
| **X-Content-Type-Options** | Prevent MIME sniffing | `nosniff` |
| **X-Frame-Options** | Prevent clickjacking | `DENY` |
| **X-XSS-Protection** | Enable XSS filtering | `1; mode=block` |
| **Strict-Transport-Security** | Enforce HTTPS | `max-age=31536000` |
| **Referrer-Policy** | Control referrer info | `strict-origin-when-cross-origin` |
| **Content-Security-Policy** | Control resource loading | `default-src 'self'` |

## 📁 File Upload Security

### Upload Configuration

```python
# core/config.py
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}
UPLOAD_DIR = "uploads/"

# File size limits by type
IMAGE_SIZE_LIMIT = 5 * 1024 * 1024  # 5MB for images
DOCUMENT_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB for documents
```

### File Validation

```python
# utils/security.py
class FileSecurity:
    @staticmethod
    def validate_file_type(filename: str, allowed_types: set) -> bool:
        """Validate file extension"""
        return Path(filename).suffix.lower() in allowed_types

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Remove dangerous characters from filename"""
        import re
        return re.sub(r'[<>:"/\\|?*]', '_', filename)

    @staticmethod
    def generate_secure_filename(original_filename: str, user_id: str) -> str:
        """Generate secure unique filename"""
        file_extension = Path(original_filename).suffix
        sanitized_name = FileSecurity.sanitize_filename(original_filename)
        unique_id = uuid.uuid4().hex[:8]
        return f"{user_id}_{unique_id}{file_extension}"
```

### Upload Flow

```mermaid
graph TD
    A[User Upload Request] --> B[Validate File Size]
    B --> C{Size OK?}
    C -->|No| D[Reject Upload]
    C -->|Yes| E[Validate File Type]
    E --> F{Type OK?}
    F -->|No| G[Reject Upload]
    F -->|Yes| H[Sanitize Filename]
    H --> I[Generate Unique Name]
    I --> J[Save to Secure Location]
    J --> K[Store File Reference]
```

## 📝 Audit Logging

### Logging Configuration

```python
# main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Separate security logger
security_logger = logging.getLogger('security')
security_handler = logging.FileHandler('security.log')
security_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
security_logger.addHandler(security_handler)
```

### Logged Events

| Event Type | Description | Log Level |
|------------|-------------|-----------|
| **Authentication** | Login/logout events | INFO |
| **Authorization** | Permission denied | WARNING |
| **Data Access** | Sensitive data access | INFO |
| **File Upload** | File operations | INFO |
| **Payment** | Financial transactions | INFO |
| **Admin Actions** | Administrative operations | WARNING |
| **Security Events** | Failed attacks, breaches | ERROR |

### Security Log Format

```json
{
  "timestamp": "2025-01-04T16:08:51+05:30",
  "level": "WARNING",
  "event": "unauthorized_access",
  "user_id": "u_abc123def4",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "endpoint": "/admin/users",
  "method": "GET",
  "status_code": 403,
  "details": "User attempted to access admin endpoint without permission"
}
```

## 🔐 Advanced Security Features

### 1. Request Size Limiting

```python
# middleware/security.py
class RequestSizeLimitMiddleware:
    def __init__(self, app, max_size: int = 5242880):  # 5MB
        self.app = app
        self.max_size = max_size

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Intercept request body
            body = b""
            more_body = True

            async def receive_with_limit():
                nonlocal body, more_body
                if more_body:
                    message = await receive()
                    if message["type"] == "http.request":
                        body += message.get("body", b"")
                        if len(body) > self.max_size:
                            # Send error response
                            error_response = {
                                "type": "http.response.start",
                                "status": 413,
                                "headers": [[b"content-type", b"application/json"]],
                            }
                            await send(error_response)
                            return
                    if not message.get("more_body"):
                        more_body = False
                return message

            scope["receive"] = receive_with_limit
        await self.app(scope, receive, send)
```

### 2. Security Logging Middleware

```python
# middleware/security.py
class SecurityLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract request information
            request_info = {
                "method": scope.get("method"),
                "path": scope.get("path"),
                "query_string": scope.get("query_string"),
                "client_ip": self.get_client_ip(scope),
                "user_agent": self.get_header(scope, b"user-agent"),
                "timestamp": datetime.now(IST).isoformat()
            }

            # Log security-relevant requests
            if self.is_security_event(request_info):
                security_logger.warning(f"Security event: {request_info}")

        await self.app(scope, receive, send)

    def get_client_ip(self, scope) -> str:
        """Extract client IP address"""
        for header in [b"x-forwarded-for", b"x-real-ip"]:
            value = self.get_header(scope, header)
            if value:
                return value.split(",")[0].strip()
        return scope.get("client")[0] if scope.get("client") else "unknown"
```

### 3. CORS Configuration

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-User-ID"],
    max_age=3600,  # Cache preflight response
)
```

## 🚨 Security Monitoring

### Health Check Security

```python
@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Enhanced health check with security monitoring"""
    # Database connection test
    # Memory usage check
    # Cache health verification
    # Security metrics

    return {
        "status": "healthy",
        "security": {
            "failed_login_attempts": get_failed_login_count(),
            "suspicious_activities": get_suspicious_activity_count(),
            "rate_limit_hits": get_rate_limit_hit_count()
        }
    }
```

### Security Metrics

**Monitored Metrics:**
- Failed authentication attempts
- Rate limit violations
- Suspicious IP addresses
- SQL injection attempts
- XSS attack attempts
- File upload violations

## 🔧 Security Best Practices

### 1. Environment Security

```bash
# .env file security
JWT_SECRET=your-super-secret-jwt-key-here
RAZORPAY_KEY_SECRET=your-razorpay-secret
DATABASE_URL=postgresql://user:password@localhost/db

# Never commit secrets to version control
# Use environment-specific values
# Rotate secrets regularly
```

### 2. Database Security

```sql
-- Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create security policies
CREATE POLICY user_isolation ON users
FOR ALL USING (auth.uid() = id);

-- Audit triggers
CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS trigger AS $$
BEGIN
    INSERT INTO audit_log (table_name, operation, old_data, new_data, user_id)
    VALUES (TG_TABLE_NAME, TG_OP, OLD, NEW, current_user_id);
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

### 3. API Security

- **Input validation** on all endpoints
- **Output encoding** to prevent XSS
- **Error handling** without information leakage
- **API versioning** for breaking changes
- **Request/response logging** for audit trails

## 🚨 Incident Response

### Security Incident Procedure

1. **Detection**: Monitor logs for suspicious activity
2. **Assessment**: Evaluate the severity and scope
3. **Containment**: Isolate affected systems
4. **Recovery**: Restore normal operations
5. **Lessons Learned**: Update security measures

### Emergency Contacts

- **Security Team**: security@yourcompany.com
- **Infrastructure**: infra@yourcompany.com
- **Database Admin**: dba@yourcompany.com

---

## 📚 Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OAuth 2.0 Security](https://tools.ietf.org/html/rfc6819)

---

*Last Updated: January 2025*
*Security Version: v2.0.0*
