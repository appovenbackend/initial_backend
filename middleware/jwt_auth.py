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
            "/events/",  # Public event listing and details
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
                # Safe access to request attributes
                try:
                    method = request.method
                    path = request.url.path
                    client_host = getattr(request.client, 'host', 'unknown')
                except:
                    method = 'UNKNOWN'
                    path = 'UNKNOWN'
                    client_host = 'unknown'

                logger.warning(f"No Authorization header for {method} {path} from {client_host}")
                return self._unauthorized_response("Missing Authorization header", request_id)

            # Parse Bearer token
            try:
                scheme, token = auth_header.split(" ", 1)
                if scheme.lower() != "bearer":
                    method = getattr(request, 'method', 'UNKNOWN')
                    path = getattr(getattr(request, 'url', None), 'path', 'UNKNOWN') if hasattr(request, 'url') else 'UNKNOWN'
                    logger.warning(f"Invalid auth scheme '{scheme}' for {method} {path}")
                    return self._unauthorized_response("Invalid authorization scheme. Expected 'Bearer'", request_id)
            except ValueError:
                method = getattr(request, 'method', 'UNKNOWN')
                path = getattr(getattr(request, 'url', None), 'path', 'UNKNOWN') if hasattr(request, 'url') else 'UNKNOWN'
                logger.warning(f"Malformed auth header '{auth_header}' for {method} {path}")
                return self._unauthorized_response("Invalid authorization header format. Expected 'Bearer <token>'", request_id)

            # Validate JWT token
            try:
                payload = jwt_security_manager.verify_token(token)
                user_id = payload.get("sub")

                if not user_id:
                    method = getattr(request, 'method', 'UNKNOWN')
                    path = getattr(getattr(request, 'url', None), 'path', 'UNKNOWN') if hasattr(request, 'url') else 'UNKNOWN'
                    logger.warning(f"No user_id in token payload for {method} {path}")
                    return self._unauthorized_response("Invalid token payload - missing user ID", request_id)

                # Set user context in request state (CRITICAL FIX)
                request.state.user_id = user_id
                request.state.user_role = payload.get("role", "user")
                request.state.jwt_payload = payload

                logger.info(f"✅ Authenticated user {user_id} for {method} {path}")
                logger.info(f"✅ Set request.state.user_id = {user_id}")

            except HTTPException as e:
                method = getattr(request, 'method', 'UNKNOWN')
                path = getattr(getattr(request, 'url', None), 'path', 'UNKNOWN') if hasattr(request, 'url') else 'UNKNOWN'
                logger.warning(f"JWT validation failed for {method} {path}: {e.detail}")
                return self._unauthorized_response(e.detail, request_id)
            except JWTError as e:
                method = getattr(request, 'method', 'UNKNOWN')
                path = getattr(getattr(request, 'url', None), 'path', 'UNKNOWN') if hasattr(request, 'url') else 'UNKNOWN'
                logger.warning(f"JWT decode error for {method} {path}: {str(e)}")
                return self._unauthorized_response("Invalid or expired token", request_id)
            except Exception as e:
                method = getattr(request, 'method', 'UNKNOWN')
                path = getattr(getattr(request, 'url', None), 'path', 'UNKNOWN') if hasattr(request, 'url') else 'UNKNOWN'
                logger.error(f"Unexpected JWT error for {method} {path}: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                return self._unauthorized_response("Authentication error", request_id)

            # Process request with authenticated user
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-User-ID"] = user_id  # For backward compatibility during transition

            return response

        except Exception as e:
            # Get request_id safely, with fallback
            try:
                request_id = getattr(request.state, 'request_id', 'unknown')
            except:
                request_id = 'unknown'

            # Get method and path safely
            try:
                method = request.method
                path = request.url.path
            except:
                method = 'UNKNOWN'
                path = 'UNKNOWN'

            logger.error(f"JWT middleware error for {method} {path}: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Authentication middleware error",
                    "request_id": request_id,
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
    Dependency to get current user ID from JWT token
    Handles JWT validation directly since FastAPI dependencies bypass middleware
    """
    # First check if middleware already set user_id (for backward compatibility)
    user_id = getattr(request.state, 'user_id', None)
    if user_id:
        return user_id

    # If not set by middleware, extract and validate JWT token directly
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.warning(f"No Authorization header for {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )

    # Parse Bearer token
    try:
        scheme, token = auth_header.split(" ", 1)
        if scheme.lower() != "bearer":
            logger.warning(f"Invalid auth scheme '{scheme}' for {request.method} {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization scheme. Expected 'Bearer'"
            )
    except ValueError:
        logger.warning(f"Malformed auth header '{auth_header}' for {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )

    # Validate JWT token
    try:
        payload = jwt_security_manager.verify_token(token)
        user_id = payload.get("sub")

        if not user_id:
            logger.warning(f"No user_id in token payload for {request.method} {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload - missing user ID"
            )

        # Set user context in request state for other middlewares/dependencies
        request.state.user_id = user_id
        request.state.user_role = payload.get("role", "user")
        request.state.jwt_payload = payload

        logger.info(f"✅ Authenticated user {user_id} for {request.method} {request.url.path} via dependency")

        return user_id

    except HTTPException:
        raise
    except JWTError as e:
        logger.warning(f"JWT decode error for {request.method} {request.url.path}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except Exception as e:
        logger.error(f"Unexpected JWT error for {request.method} {request.url.path}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication error"
        )


def get_current_user_role(request: Request) -> str:
    """Get current user role from JWT middleware or dependency"""
    # First check if middleware already set user_role (for backward compatibility)
    role = getattr(request.state, 'user_role', None)
    if role:
        return role

    # If not set by middleware, extract from JWT token directly (same as get_current_user_id)
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.warning(f"No Authorization header for role check: {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )

    # Parse Bearer token
    try:
        scheme, token = auth_header.split(" ", 1)
        if scheme.lower() != "bearer":
            logger.warning(f"Invalid auth scheme for role check '{scheme}' for {request.method} {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization scheme. Expected 'Bearer'"
            )
    except ValueError:
        logger.warning(f"Malformed auth header for role check '{auth_header}' for {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )

    # Validate JWT token and extract role
    try:
        payload = jwt_security_manager.verify_token(token)
        role = payload.get("role", "user")

        # Set user context in request state for other middlewares/dependencies
        request.state.user_id = payload.get("sub")
        request.state.user_role = role
        request.state.jwt_payload = payload

        logger.info(f"✅ Retrieved role '{role}' for user {payload.get('sub')} via dependency")

        return role

    except HTTPException:
        raise
    except JWTError as e:
        logger.warning(f"JWT decode error for role check {request.method} {request.url.path}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    except Exception as e:
        logger.error(f"Unexpected JWT error for role check {request.method} {request.url.path}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication error"
        )


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
