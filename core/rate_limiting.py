"""
Advanced Rate Limiting with Generous User Allowances
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
import redis
from typing import Optional
from core.config import REDIS_URL
from jose import jwt, JWTError
from core.config import SECRET_KEY, ALGORITHM

class AdvancedRateLimiter:
    def __init__(self):
        self.redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None
        
    def get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from JWT token for authenticated requests"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                return payload.get("sub")
            except:
                return None
        return None

# Rate limiting strategies with generous limits
def get_rate_limit_key(request: Request) -> str:
    """Multi-tier rate limiting based on user authentication"""
    # For now, disable user-based rate limiting to fix auth issues
    # TODO: Re-enable after fixing authentication flow
    return f"ip:{get_remote_address(request)}"  # IP-based for all requests

# Generous rate limits for different endpoint types
AUTH_RATE_LIMITS = {
    "login": "20/minute",           # Generous for login attempts
    "register": "10/minute",        # Allow multiple registrations
    "password_reset": "5/minute",   # Reasonable for password reset
    "otp_request": "10/minute",     # Allow multiple OTP requests
    "google_auth": "30/minute"      # Very generous for OAuth
}

API_RATE_LIMITS = {
    "public_read": "500/minute",      # Very generous for public endpoints
    "authenticated": "1000/minute",   # Very generous for authenticated users
    "admin": "2000/minute",          # Very generous for admin operations
    "payment": "50/minute",          # Reasonable for payment operations
    "file_upload": "20/minute",      # Reasonable for file uploads
    "event_creation": "100/minute",  # Generous for event creation
    "ticket_operations": "200/minute", # Generous for ticket operations
    "social_operations": "300/minute"  # Very generous for social features
}

# Create limiter instance
limiter = Limiter(key_func=get_rate_limit_key)

# Convenience functions for common rate limits
def auth_rate_limit(endpoint: str):
    """Apply authentication rate limiting"""
    return limiter.limit(AUTH_RATE_LIMITS.get(endpoint, "10/minute"))

def api_rate_limit(endpoint: str):
    """Apply API rate limiting"""
    return limiter.limit(API_RATE_LIMITS.get(endpoint, "100/minute"))

def generous_rate_limit(limit: str):
    """Apply custom generous rate limit"""
    return limiter.limit(limit)
