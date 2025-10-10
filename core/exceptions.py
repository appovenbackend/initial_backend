"""
Comprehensive Error Handling System
Provides centralized exception handling with proper categorization and logging
"""
from enum import Enum
from typing import Optional, Dict, Any
import logging
from datetime import datetime
from core.config import IST

logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    """Categorize errors for better handling and reporting"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    PAYMENT = "payment"
    EXTERNAL_API = "external_api"
    RATE_LIMIT = "rate_limit"
    SECURITY = "security"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"

class ErrorSeverity(Enum):
    """Define error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class BaseCustomException(Exception):
    """Base class for all custom exceptions with frontend-friendly structure"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_message: Optional[str] = None,
        field: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.status_code = status_code
        self.error_code = error_code or f"{category.value.upper()}_001"
        self.details = details or {}
        self.request_id = request_id
        self.user_message = user_message or self._generate_user_message()
        self.field = field
        self.timestamp = datetime.now(IST).isoformat()

    def _generate_user_message(self) -> str:
        """Generate user-friendly message from technical message"""
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response (legacy format)"""
        return {
            "error": True,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "status_code": self.status_code,
            "details": self.details,
            "request_id": self.request_id,
            "timestamp": self.timestamp
        }

    def to_frontend_dict(self, request_path: str = None, request_method: str = None) -> Dict[str, Any]:
        """Convert exception to frontend-friendly dictionary"""
        response = {
            "success": False,
            "error": {
                "type": self._get_error_type(),
                "code": self.error_code,
                "message": self.message,
                "userMessage": self.user_message,
                "severity": self.severity.value
            },
            "meta": {
                "requestId": self.request_id,
                "timestamp": self.timestamp
            }
        }

        # Add path and method if provided
        if request_path or request_method:
            response["meta"]["path"] = request_path
            response["meta"]["method"] = request_method

        # Add field-specific error information for validation errors
        if self.field:
            response["error"]["field"] = self.field

        # Add field errors for validation errors with multiple fields
        if self.category == ErrorCategory.VALIDATION and self.details:
            field_errors = self._extract_field_errors()
            if field_errors:
                response["error"]["fieldErrors"] = field_errors

        return response

    def _get_error_type(self) -> str:
        """Get frontend-friendly error type"""
        type_mapping = {
            ErrorCategory.VALIDATION: "validation_error",
            ErrorCategory.AUTHENTICATION: "authentication_error",
            ErrorCategory.AUTHORIZATION: "authorization_error",
            ErrorCategory.DATABASE: "database_error",
            ErrorCategory.PAYMENT: "payment_error",
            ErrorCategory.EXTERNAL_API: "external_api_error",
            ErrorCategory.RATE_LIMIT: "rate_limit_error",
            ErrorCategory.SECURITY: "security_error",
            ErrorCategory.BUSINESS_LOGIC: "business_logic_error",
            ErrorCategory.SYSTEM: "system_error"
        }
        return type_mapping.get(self.category, "unknown_error")

    def _extract_field_errors(self) -> Dict[str, Any]:
        """Extract field-specific errors from details"""
        field_errors = {}

        if isinstance(self.details, dict):
            for key, value in self.details.items():
                if isinstance(value, dict) and "field" in value:
                    field_name = value["field"]
                    field_errors[field_name] = {
                        "message": value.get("message", self.message),
                        "code": value.get("code", self.error_code),
                        "severity": value.get("severity", self.severity.value)
                    }

        return field_errors

# Validation Errors
class ValidationError(BaseCustomException):
    """Raised when input validation fails"""
    def __init__(self, message: str, details: Optional[Dict] = None, **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            status_code=400,
            details=details,
            **kwargs
        )

class EventValidationError(ValidationError):
    """Raised when event-specific validation fails"""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = {"field": field} if field else {}
        super().__init__(message, details=details, **kwargs)
        self.error_code = "VALIDATION_EVENT_001"

class UserValidationError(ValidationError):
    """Raised when user-specific validation fails"""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = {"field": field} if field else {}
        super().__init__(message, details=details, **kwargs)
        self.error_code = "VALIDATION_USER_001"

# Authentication & Authorization Errors
class AuthenticationError(BaseCustomException):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            status_code=401,
            error_code="AUTH_001",
            **kwargs
        )

class AuthorizationError(BaseCustomException):
    """Raised when authorization fails"""
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            status_code=403,
            error_code="AUTHZ_001",
            **kwargs
        )

class JWTError(AuthenticationError):
    """Raised when JWT token processing fails"""
    def __init__(self, message: str = "Invalid or expired token", **kwargs):
        super().__init__(message, **kwargs)
        self.error_code = "AUTH_JWT_001"

# Database Errors
class DatabaseError(BaseCustomException):
    """Raised when database operations fail"""
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = {"operation": operation} if operation else {}
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            status_code=500,
            error_code="DB_001",
            details=details,
            **kwargs
        )

class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    def __init__(self, message: str = "Database connection failed", **kwargs):
        super().__init__(message, **kwargs)
        self.error_code = "DB_CONN_001"
        self.severity = ErrorSeverity.CRITICAL

class DatabaseTimeoutError(DatabaseError):
    """Raised when database operations timeout"""
    def __init__(self, message: str = "Database operation timeout", **kwargs):
        super().__init__(message, **kwargs)
        self.error_code = "DB_TIMEOUT_001"

# Payment Errors
class PaymentError(BaseCustomException):
    """Raised when payment processing fails"""
    def __init__(self, message: str, payment_id: Optional[str] = None, **kwargs):
        details = {"payment_id": payment_id} if payment_id else {}
        super().__init__(
            message=message,
            category=ErrorCategory.PAYMENT,
            severity=ErrorSeverity.HIGH,
            status_code=402,
            error_code="PAYMENT_001",
            details=details,
            **kwargs
        )

class PaymentVerificationError(PaymentError):
    """Raised when payment verification fails"""
    def __init__(self, message: str = "Payment verification failed", **kwargs):
        super().__init__(message, **kwargs)
        self.error_code = "PAYMENT_VERIFY_001"

# External API Errors
class ExternalAPIError(BaseCustomException):
    """Raised when external API calls fail"""
    def __init__(self, message: str, service: Optional[str] = None, **kwargs):
        details = {"service": service} if service else {}
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_API,
            severity=ErrorSeverity.MEDIUM,
            status_code=502,
            error_code="EXTERNAL_API_001",
            details=details,
            **kwargs
        )

# WhatsApp exception removed

# Business Logic Errors
class BusinessLogicError(BaseCustomException):
    """Raised when business rules are violated"""
    def __init__(self, message: str, rule: Optional[str] = None, **kwargs):
        details = {"rule": rule} if rule else {}
        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            status_code=400,
            error_code="BUSINESS_001",
            details=details,
            **kwargs
        )

class EventNotFoundError(BusinessLogicError):
    """Raised when requested event is not found"""
    def __init__(self, event_id: Optional[str] = None, **kwargs):
        message = "Event not found"
        details = {"event_id": event_id} if event_id else {}
        super().__init__(message, details=details, **kwargs)
        self.error_code = "EVENT_NOT_FOUND_001"

class EventExpiredError(BusinessLogicError):
    """Raised when event has expired"""
    def __init__(self, event_id: Optional[str] = None, **kwargs):
        message = "Event has expired"
        details = {"event_id": event_id} if event_id else {}
        super().__init__(message, details=details, **kwargs)
        self.error_code = "EVENT_EXPIRED_001"

class DuplicateRegistrationError(BusinessLogicError):
    """Raised when user tries to register for same event twice"""
    def __init__(self, event_id: Optional[str] = None, user_id: Optional[str] = None, **kwargs):
        message = "User already registered for this event"
        details = {"event_id": event_id, "user_id": user_id}
        super().__init__(message, details=details, **kwargs)
        self.error_code = "DUPLICATE_REG_001"

# Rate Limiting Errors
class RateLimitError(BaseCustomException):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        super().__init__(
            message=message,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.LOW,
            status_code=429,
            error_code="RATE_LIMIT_001",
            **kwargs
        )

# Security Errors
class SecurityError(BaseCustomException):
    """Raised when security violations are detected"""
    def __init__(self, message: str, violation_type: Optional[str] = None, **kwargs):
        details = {"violation_type": violation_type} if violation_type else {}
        super().__init__(
            message=message,
            category=ErrorCategory.SECURITY,
            severity=ErrorSeverity.CRITICAL,
            status_code=403,
            error_code="SECURITY_001",
            details=details,
            **kwargs
        )

class SQLInjectionError(SecurityError):
    """Raised when potential SQL injection is detected"""
    def __init__(self, message: str = "Potential SQL injection detected", **kwargs):
        super().__init__(message, violation_type="sql_injection", **kwargs)
        self.error_code = "SQL_INJECTION_001"

# System Errors
class SystemError(BaseCustomException):
    """Raised when system-level errors occur"""
    def __init__(self, message: str, component: Optional[str] = None, **kwargs):
        details = {"component": component} if component else {}
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            status_code=500,
            error_code="SYSTEM_001",
            details=details,
            **kwargs
        )

class CacheError(SystemError):
    """Raised when cache operations fail"""
    def __init__(self, message: str = "Cache operation failed", **kwargs):
        super().__init__(message, component="cache", **kwargs)
        self.error_code = "CACHE_001"

class ConfigurationError(SystemError):
    """Raised when configuration errors occur"""
    def __init__(self, message: str = "Configuration error", **kwargs):
        super().__init__(message, component="config", **kwargs)
        self.error_code = "CONFIG_001"

# Error Handler Functions
def handle_database_error(error: Exception, operation: str = None) -> DatabaseError:
    """Convert database exceptions to custom exceptions"""
    error_msg = str(error).lower()

    if "connection" in error_msg or "timeout" in error_msg:
        if "timeout" in error_msg:
            return DatabaseTimeoutError(f"Database timeout during {operation or 'operation'}")
        else:
            return DatabaseConnectionError(f"Database connection failed during {operation or 'operation'}")
    else:
        return DatabaseError(f"Database error during {operation or 'operation'}: {str(error)}", operation)

def handle_validation_error(error: Exception, field: str = None) -> ValidationError:
    """Convert validation exceptions to custom exceptions"""
    if isinstance(error, ValidationError):
        return error

    return ValidationError(f"Validation failed: {str(error)}", details={"field": field})

def log_error(error: BaseCustomException, request = None):
    """Log error with appropriate level based on severity"""
    log_data = {
        "error_code": error.error_code,
        "category": error.category.value,
        "severity": error.severity.value,
        "message": error.message,
        "request_id": error.request_id,
        "path": request.url.path if request else None,
        "method": request.method if request else None,
        "client_ip": request.client.host if request else None
    }

    if error.severity == ErrorSeverity.CRITICAL:
        logger.critical("Critical error occurred", extra=log_data)
    elif error.severity == ErrorSeverity.HIGH:
        logger.error("High severity error occurred", extra=log_data)
    elif error.severity == ErrorSeverity.MEDIUM:
        logger.warning("Medium severity error occurred", extra=log_data)
    else:
        logger.info("Low severity error occurred", extra=log_data)

    # Also log to structured logging if available
    try:
        from utils.structured_logging import track_error
        if request:
            track_error(error.error_code, error.message, request=request)
    except ImportError:
        pass  # Structured logging not available
