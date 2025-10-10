"""
Comprehensive Error Handling Middleware
Catches and formats all exceptions with proper logging and response formatting
"""
import traceback
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi.errors import RateLimitExceeded
from core.exceptions import (
    BaseCustomException,
    ErrorCategory,
    ErrorSeverity,
    log_error,
    handle_database_error,
    handle_validation_error
)

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Comprehensive error handling middleware"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracking
        request_id = getattr(request.state, 'request_id', 'unknown')

        try:
            # Process the request
            response = await call_next(request)

            # Log successful requests (optional, can be expensive)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "client_ip": request.client.host
                    }
                )

            return response

        except BaseCustomException as e:
            # Handle custom exceptions
            e.request_id = request_id
            log_error(e, request)
            return self._create_error_response(e, request)

        except RateLimitExceeded as e:
            # Handle rate limiting
            from core.exceptions import RateLimitError
            rate_limit_error = RateLimitError(request_id=request_id)
            log_error(rate_limit_error, request)
            return self._create_error_response(rate_limit_error, request)

        except HTTPException as e:
            # Handle FastAPI HTTP exceptions
            custom_error = self._convert_http_exception(e, request_id)
            log_error(custom_error, request)
            return self._create_error_response(custom_error, request)

        except Exception as e:
            # Handle unexpected exceptions
            unexpected_error = self._handle_unexpected_error(e, request, request_id)
            log_error(unexpected_error, request)
            return self._create_error_response(unexpected_error, request)

    def _create_error_response(self, error: BaseCustomException, request: Request = None) -> JSONResponse:
        """Create standardized error response with frontend-friendly format"""
        # Use frontend-friendly format for better client integration
        request_path = request.url.path if request else None
        request_method = request.method if request else None

        frontend_response = error.to_frontend_dict(request_path, request_method)

        # Add rate limit headers for rate limiting errors
        headers = {
            "X-Error-Code": error.error_code,
            "X-Error-Category": error.category.value,
            "X-Request-ID": error.request_id or "unknown"
        }

        if error.category.value == "rate_limit":
            headers["Retry-After"] = "60"  # Suggest retry after 60 seconds

        return JSONResponse(
            status_code=error.status_code,
            content=frontend_response,
            headers=headers
        )

    def _convert_http_exception(self, exc: HTTPException, request_id: str) -> BaseCustomException:
        """Convert FastAPI HTTPException to custom exception"""
        # Map common HTTP status codes to appropriate custom exceptions
        if exc.status_code == 400:
            return handle_validation_error(exc, request_id=request_id)
        elif exc.status_code == 401:
            from core.exceptions import AuthenticationError
            return AuthenticationError(exc.detail, request_id=request_id)
        elif exc.status_code == 403:
            from core.exceptions import AuthorizationError
            return AuthorizationError(exc.detail, request_id=request_id)
        elif exc.status_code == 404:
            from core.exceptions import BusinessLogicError
            return BusinessLogicError(exc.detail, request_id=request_id)
        else:
            from core.exceptions import SystemError
            return SystemError(exc.detail, request_id=request_id)

    def _handle_unexpected_error(self, exc: Exception, request: Request, request_id: str) -> BaseCustomException:
        """Handle unexpected exceptions with proper logging"""
        # Log full traceback for debugging
        logger.error(
            f"Unexpected error in {request.method} {request.url.path}: {str(exc)}",
            extra={
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host,
                "traceback": traceback.format_exc()
            }
        )

        # Determine error category based on exception type
        error_msg = str(exc).lower()

        if any(keyword in error_msg for keyword in ["database", "connection", "sql"]):
            return handle_database_error(exc, request_id=request_id)
        elif any(keyword in error_msg for keyword in ["permission", "unauthorized", "forbidden"]):
            from core.exceptions import AuthorizationError
            return AuthorizationError(str(exc), request_id=request_id)
        elif any(keyword in error_msg for keyword in ["validation", "invalid", "format"]):
            return handle_validation_error(exc, request_id=request_id)
        else:
            from core.exceptions import SystemError
            return SystemError(f"An unexpected error occurred: {str(exc)}", request_id=request_id)

# Database operation wrapper with error handling
def handle_database_operation(operation_name: str):
    """Decorator to handle database operations with proper error handling"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                db_error = handle_database_error(e, operation_name)
                raise db_error
        return wrapper
    return decorator

# Async database operation wrapper
async def handle_async_database_operation(operation_name: str):
    """Decorator for async database operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                db_error = handle_database_error(e, operation_name)
                raise db_error
        return wrapper
    return decorator

# External API call wrapper
def handle_external_api_call(service_name: str):
    """Decorator to handle external API calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                from core.exceptions import ExternalAPIError
                api_error = ExternalAPIError(
                    f"External API call to {service_name} failed: {str(e)}",
                    service=service_name
                )
                raise api_error
        return wrapper
    return decorator

# Business logic validation wrapper
def validate_business_logic(rule_name: str):
    """Decorator for business logic validation"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                from core.exceptions import BusinessLogicError
                business_error = BusinessLogicError(
                    f"Business rule '{rule_name}' violated: {str(e)}",
                    rule=rule_name
                )
                raise business_error
        return wrapper
    return decorator

# Error response helper functions
def create_validation_error_response(field: str, message: str, request_id: str = None):
    """Create a validation error response"""
    from core.exceptions import ValidationError
    error = ValidationError(message, details={"field": field}, request_id=request_id)
    return error.to_dict(), error.status_code

def create_not_found_error_response(resource: str, resource_id: str = None, request_id: str = None):
    """Create a not found error response"""
    from core.exceptions import BusinessLogicError
    message = f"{resource} not found"
    details = {"resource_id": resource_id} if resource_id else {}
    error = BusinessLogicError(message, details=details, request_id=request_id)
    return error.to_dict(), error.status_code

def create_unauthorized_error_response(message: str = "Unauthorized access", request_id: str = None):
    """Create an unauthorized error response"""
    from core.exceptions import AuthorizationError
    error = AuthorizationError(message, request_id=request_id)
    return error.to_dict(), error.status_code

def create_server_error_response(message: str = "Internal server error", request_id: str = None):
    """Create a server error response"""
    from core.exceptions import SystemError
    error = SystemError(message, request_id=request_id)
    return error.to_dict(), error.status_code
