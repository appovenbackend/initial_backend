"""
Security Configuration and Environment Variables
Comprehensive security setup for production deployment
"""
import os
from typing import List, Dict, Any

# Security Configuration
class SecurityConfig:
    """Centralized security configuration"""
    
    # JWT Configuration
    JWT_SECRET = os.getenv("JWT_SECRET")  # MUST be set in production
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL")  # MUST be set in production
    DATABASE_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # MUST be set in production
    
    # Payment Configuration
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")  # MUST be set in production
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")  # MUST be set in production
    RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")  # MUST be set in production
    
    # OAuth Configuration
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    
    # Redis Configuration
    REDIS_URL = os.getenv("REDIS_URL", "localhost:6379")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS = ["*"]
    
    # Security Headers
    ENABLE_SECURITY_HEADERS = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"
    ENABLE_REQUEST_LOGGING = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_STORAGE_URL = os.getenv("RATE_LIMIT_STORAGE_URL", "memory://")
    
    # Request Size Limits
    MAX_REQUEST_SIZE = int(os.getenv("MAX_REQUEST_SIZE", "5242880"))  # 5MB
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
    ERROR_LOG_FILE = os.getenv("ERROR_LOG_FILE", "logs/errors.log")
    SECURITY_LOG_FILE = os.getenv("SECURITY_LOG_FILE", "logs/security.log")
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # Notification Configuration
    NOTIFICATION_ENABLED = os.getenv("NOTIFICATION_ENABLED", "true").lower() == "true"
    EMAIL_SERVICE_URL = os.getenv("EMAIL_SERVICE_URL")
    SMS_SERVICE_URL = os.getenv("SMS_SERVICE_URL")
    WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL")
    
    # Monitoring Configuration
    MONITORING_ENABLED = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
    METRICS_ENDPOINT = os.getenv("METRICS_ENDPOINT", "/metrics")
    HEALTH_CHECK_ENDPOINT = os.getenv("HEALTH_CHECK_ENDPOINT", "/health")
    
    @classmethod
    def validate_production_config(cls) -> List[str]:
        """Validate production configuration"""
        errors = []
        
        if cls.ENVIRONMENT.lower() == "production":
            required_vars = [
                "JWT_SECRET",
                "DATABASE_URL",
                "RAZORPAY_KEY_ID",
                "RAZORPAY_KEY_SECRET",
                "RAZORPAY_WEBHOOK_SECRET"
            ]
            
            for var in required_vars:
                if not getattr(cls, var):
                    errors.append(f"Missing required environment variable: {var}")
            
            # Check for default/weak values
            if cls.JWT_SECRET == "supersecretkey123":
                errors.append("JWT_SECRET is using default value - must be changed in production")
            
            if cls.CORS_ORIGINS == ["*"]:
                errors.append("CORS_ORIGINS is set to wildcard - should be restricted in production")
            
            if cls.DEBUG:
                errors.append("DEBUG is enabled - should be disabled in production")
        
        return errors
    
    @classmethod
    def get_security_headers(cls) -> Dict[str, str]:
        """Get security headers configuration"""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        if cls.ENVIRONMENT.lower() == "production":
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return headers
    
    @classmethod
    def get_csp_policy(cls) -> str:
        """Get Content Security Policy"""
        if cls.ENVIRONMENT.lower() == "production":
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://checkout.razorpay.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.razorpay.com; "
                "frame-src 'self' https://checkout.razorpay.com;"
            )
        else:
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://checkout.razorpay.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.razorpay.com https://accounts.google.com; "
                "frame-src 'self' https://accounts.google.com https://checkout.razorpay.com;"
            )

# Global security config instance
security_config = SecurityConfig()

# Validation function
def validate_security_config() -> bool:
    """Validate security configuration"""
    errors = security_config.validate_production_config()
    
    if errors:
        print("❌ Security configuration validation failed:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print("✅ Security configuration validation passed")
    return True

# Environment variable template
ENVIRONMENT_TEMPLATE = """
# Security Configuration
JWT_SECRET=your_secure_jwt_secret_here
ENCRYPTION_KEY=your_encryption_key_here

# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/database

# Payment Configuration
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_razorpay_webhook_secret

# OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password

# CORS Configuration (comma-separated)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Security Settings
ENVIRONMENT=production
DEBUG=false
ENABLE_SECURITY_HEADERS=true
ENABLE_REQUEST_LOGGING=true

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Notification Configuration
NOTIFICATION_ENABLED=true
EMAIL_SERVICE_URL=your_email_service_url
SMS_SERVICE_URL=your_sms_service_url
# WhatsApp service removed

# Monitoring Configuration
MONITORING_ENABLED=true
METRICS_ENDPOINT=/metrics
HEALTH_CHECK_ENDPOINT=/health
"""

if __name__ == "__main__":
    print("Security Configuration Validation")
    print("=" * 40)
    validate_security_config()
    
    print("\nEnvironment Variables Template")
    print("=" * 40)
    print(ENVIRONMENT_TEMPLATE)
