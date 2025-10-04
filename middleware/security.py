"""
Security Headers and Request Size Limiting Middleware
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import os
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy (relaxed for development)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://accounts.google.com https://checkout.razorpay.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.razorpay.com https://accounts.google.com; "
            "frame-src https://accounts.google.com https://checkout.razorpay.com;"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HSTS (only in production)
        if os.getenv("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            logger.warning(f"Request too large: {content_length} bytes from {request.client.host}")
            return Response(
                content='{"error": "Request too large", "detail": "Maximum request size exceeded"}',
                status_code=413,
                headers={"Content-Type": "application/json"}
            )
        return await call_next(request)

class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import time
        start_time = time.time()
        
        # Log suspicious patterns
        user_agent = request.headers.get("user-agent", "")
        if any(pattern in user_agent.lower() for pattern in ["bot", "crawler", "scanner", "sqlmap", "nikto"]):
            logger.warning(f"Suspicious User-Agent: {user_agent} from {request.client.host}")
        
        # Check for common attack patterns in URL
        suspicious_paths = ["admin", "wp-admin", "phpmyadmin", "config", "backup", "test"]
        if any(pattern in request.url.path.lower() for pattern in suspicious_paths):
            logger.warning(f"Suspicious URL access: {request.url.path} from {request.client.host}")
        
        response = await call_next(request)
        
        # Log response details
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s - "
            f"IP: {request.client.host}"
        )
        
        return response
