"""
Secure Configuration Management
Handles environment variables and secrets securely
"""
import os
from typing import Optional
from dotenv import load_dotenv
import secrets
import string
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class SecureConfig:
    """Secure configuration management with validation"""
    
    def __init__(self):
        self._validate_required_secrets()
    
    def _validate_required_secrets(self):
        """Validate that all required secrets are properly configured"""
        required_secrets = [
            "JWT_SECRET",
            "DATABASE_URL",
            "RAZORPAY_KEY_ID",
            "RAZORPAY_KEY_SECRET"
        ]
        
        missing_secrets = []
        for secret in required_secrets:
            if not os.getenv(secret):
                missing_secrets.append(secret)
        
        if missing_secrets:
            logger.error(f"Missing required environment variables: {missing_secrets}")
            raise ValueError(f"Missing required environment variables: {missing_secrets}")
    
    def generate_secure_jwt_secret(self) -> str:
        """Generate a secure JWT secret"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(64))
    
    @property
    def jwt_secret(self) -> str:
        """Get JWT secret, generate if not set"""
        secret = os.getenv("JWT_SECRET")
        if not secret or secret == "supersecretkey123":
            logger.warning("Using default or weak JWT secret! Generating secure secret...")
            secret = self.generate_secure_jwt_secret()
            logger.info("Generated new JWT secret. Set JWT_SECRET environment variable to persist.")
        return secret
    
    @property
    def database_url(self) -> str:
        """Get database URL with validation"""
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL environment variable is required")
        return url
    
    @property
    def razorpay_key_id(self) -> str:
        """Get Razorpay key ID"""
        key_id = os.getenv("RAZORPAY_KEY_ID")
        if not key_id:
            raise ValueError("RAZORPAY_KEY_ID environment variable is required")
        return key_id
    
    @property
    def razorpay_key_secret(self) -> str:
        """Get Razorpay key secret"""
        key_secret = os.getenv("RAZORPAY_KEY_SECRET")
        if not key_secret:
            raise ValueError("RAZORPAY_KEY_SECRET environment variable is required")
        return key_secret
    
    @property
    def razorpay_webhook_secret(self) -> Optional[str]:
        """Get Razorpay webhook secret"""
        return os.getenv("RAZORPAY_WEBHOOK_SECRET")
    
    @property
    def google_client_id(self) -> Optional[str]:
        """Get Google OAuth client ID"""
        return os.getenv("GOOGLE_CLIENT_ID")
    
    @property
    def google_client_secret(self) -> Optional[str]:
        """Get Google OAuth client secret"""
        return os.getenv("GOOGLE_CLIENT_SECRET")
    
    @property
    def redis_url(self) -> Optional[str]:
        """Get Redis URL"""
        return os.getenv("REDIS_URL", "localhost:6379")
    
    @property
    def environment(self) -> str:
        """Get environment (development/production)"""
        return os.getenv("ENVIRONMENT", "development")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    @property
    def cors_origins(self) -> list:
        """Get CORS allowed origins"""
        origins = os.getenv("CORS_ORIGINS", "*")
        if origins == "*":
            if self.is_production:
                logger.warning("Using wildcard CORS origins in production! This is insecure.")
            return ["*"]
        return [origin.strip() for origin in origins.split(",")]
    
    @property
    def max_request_size(self) -> int:
        """Get maximum request size in bytes"""
        return int(os.getenv("MAX_REQUEST_SIZE", "5242880"))  # 5MB default
    
    @property
    def enable_security_headers(self) -> bool:
        """Check if security headers should be enabled"""
        return os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"
    
    @property
    def enable_request_logging(self) -> bool:
        """Check if request logging should be enabled"""
        return os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"
    
    @property
    def log_level(self) -> str:
        """Get log level"""
        return os.getenv("LOG_LEVEL", "INFO").upper()
    
    @property
    def access_token_expire_minutes(self) -> int:
        """Get JWT token expiration time in minutes"""
        return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    
    @property
    def refresh_token_expire_days(self) -> int:
        """Get refresh token expiration time in days"""
        return int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    @property
    def payment_currency(self) -> str:
        """Get payment currency"""
        return os.getenv("PAYMENT_CURRENCY", "INR")

    @property
    def payment_timeout_minutes(self) -> int:
        """Get payment timeout in minutes"""
        return int(os.getenv("PAYMENT_TIMEOUT_MINUTES", "10"))
    
    def validate_config(self) -> bool:
        """Validate all configuration"""
        try:
            # Test database connection
            from utils.database import get_database_session
            db = get_database_session()
            db.close()
            
            # Test Redis connection if configured
            if self.redis_url:
                from services.cache_service import is_cache_healthy
                if not is_cache_healthy():
                    logger.warning("Redis connection failed, but continuing...")
            
            logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

# Global secure config instance
secure_config = SecureConfig()

# Export commonly used values
JWT_SECRET = secure_config.jwt_secret
DATABASE_URL = secure_config.database_url
RAZORPAY_KEY_ID = secure_config.razorpay_key_id
RAZORPAY_KEY_SECRET = secure_config.razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET = secure_config.razorpay_webhook_secret
GOOGLE_CLIENT_ID = secure_config.google_client_id
GOOGLE_CLIENT_SECRET = secure_config.google_client_secret
REDIS_URL = secure_config.redis_url
ENVIRONMENT = secure_config.environment
IS_PRODUCTION = secure_config.is_production
CORS_ORIGINS = secure_config.cors_origins
MAX_REQUEST_SIZE = secure_config.max_request_size
ENABLE_SECURITY_HEADERS = secure_config.enable_security_headers
ENABLE_REQUEST_LOGGING = secure_config.enable_request_logging
LOG_LEVEL = secure_config.log_level
ACCESS_TOKEN_EXPIRE_MINUTES = secure_config.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = secure_config.refresh_token_expire_days
PAYMENT_CURRENCY = secure_config.payment_currency
PAYMENT_TIMEOUT_MINUTES = secure_config.payment_timeout_minutes
