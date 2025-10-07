"""
JWT Authentication Middleware
Replaces the insecure X-User-ID header approach with proper JWT validation
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
from core.config import SECRET_KEY, ALGORITHM
from core.jwt_security import jwt_security_manager
import logging
import uuid
from datetime import datetime
from core.config import IST

logger = logging.getLogger(__name__)

class JWTAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate JWT tokens and set user context
    Replaces the insecure X-User-ID header approach
    """
    
    def __init__(self, app, exempt_paths: list = None):
        super().__init__(app)
        # Paths that don't require authentication
        self.exempt_paths = exempt_paths or [
            "/",
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/test",
            "/openapi-test",
            "/health",
            "/auth/login",
            "/auth/register",
            "/auth/google",
            "/auth/google/callback",
            "/auth/otp/send",
            "/auth/otp/verify",
            "/auth/reset-password",
            "/payments/webhook",
            "/uploads/",
        ]
    
    async def dispatch(self, request: Request, call_next):
        try:
            # Generate request ID for tracing
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id
            
            # Check if path is exempt from authentication
            if self._is_exempt_path(request.url.path):
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                return response
            
            # Extract JWT token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                logger.warning(f"No Authorization header for {request.method} {request.url.path} from {request.client.host}")
                return self._unauthorized_response("Missing Authorization header", request_id)
            
            # Parse Bearer token
            try:
                scheme, token = auth_header.split(" ", 1)
                if scheme.lower() != "bearer":
                    return self._unauthorized_response("Invalid authorization scheme", request_id)
            except ValueError:
                return self._unauthorized_response("Invalid authorization header format", request_id)
            
            # Validate JWT token
            try:
                payload = jwt_security_manager.verify_token(token)
                user_id = payload.get("sub")
                
                if not user_id:
                    return self._unauthorized_response("Invalid token payload", request_id)
                
                # Set user context in request state
                request.state.user_id = user_id
                request.state.user_role = payload.get("role", "user")
                request.state.jwt_payload = payload
                
                logger.info(f"Authenticated user {user_id} for {request.method} {request.url.path}")
                
            except HTTPException as e:
                logger.warning(f"JWT validation failed for {request.method} {request.url.path}: {e.detail}")
                return self._unauthorized_response(e.detail, request_id)
            except JWTError as e:
                logger.warning(f"JWT decode error for {request.method} {request.url.path}: {str(e)}")
                return self._unauthorized_response("Invalid token", request_id)
            except Exception as e:
                logger.error(f"Unexpected JWT error for {request.method} {request.url.path}: {str(e)}")
                return self._unauthorized_response("Authentication error", request_id)
            
            # Process request with authenticated user
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-User-ID"] = user_id  # For backward compatibility during transition
            
            return response
            
        except Exception as e:
            logger.error(f"JWT middleware error for {request.method} {request.url.path}: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Authentication middleware error",
                    "request_id": getattr(request.state, 'request_id', 'unknown'),
                    "timestamp": datetime.now(IST).isoformat()
                }
            )
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication"""
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False
    
    def _unauthorized_response(self, detail: str, request_id: str) -> JSONResponse:
        """Create standardized unauthorized response"""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Authentication required",
                "detail": detail,
                "request_id": request_id,
                "timestamp": datetime.now(IST).isoformat()
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user_id(request: Request) -> str:
    """
    Dependency to get current user ID from JWT middleware
    Replaces the insecure X-User-ID header approach
    """
    user_id = getattr(request.state, 'user_id', None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )
    return user_id


def get_current_user_role(request: Request) -> str:
    """Get current user role from JWT middleware"""
    role = getattr(request.state, 'user_role', 'user')
    return role


def require_role(required_role: str):
    """Decorator to require specific user role"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            user_role = get_current_user_role(request)
            if user_role != required_role and user_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{required_role}' required"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator
