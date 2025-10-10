"""
Frontend-friendly error response utilities
Provides helper functions for creating consistent, client-accessible error responses
"""
from typing import Dict, Any, Optional, List
from core.exceptions import (
    ValidationError, AuthenticationError, AuthorizationError,
    BusinessLogicError, RateLimitError, SystemError
)

# Frontend-friendly error response helpers

def create_field_validation_error(field: str, message: str, code: str = None, user_message: str = None) -> ValidationError:
    """Create a field-specific validation error"""
    error_code = code or f"VALIDATION_{field.upper()}_001"
    user_msg = user_message or f"Please enter a valid {field}"

    return ValidationError(
        message=message,
        error_code=error_code,
        user_message=user_msg,
        field=field,
        details={
            "field": field,
            "message": message,
            "code": error_code
        }
    )

def create_multi_field_validation_error(field_errors: Dict[str, Dict[str, str]]) -> ValidationError:
    """Create validation error with multiple field errors"""
    # Convert field errors to the format expected by the exception
    details = {}
    for field, error_info in field_errors.items():
        details[field] = {
            "field": field,
            "message": error_info.get("message", "Invalid value"),
            "code": error_info.get("code", f"VALIDATION_{field.upper()}_001"),
            "severity": error_info.get("severity", "error")
        }

    return ValidationError(
        message="Multiple validation errors occurred",
        error_code="VALIDATION_MULTIPLE_001",
        user_message="Please correct the highlighted fields and try again",
        details=details
    )

def create_authentication_error(message: str = "Authentication failed", user_message: str = None) -> AuthenticationError:
    """Create an authentication error"""
    user_msg = user_message or "Please check your credentials and try again"

    return AuthenticationError(
        message=message,
        user_message=user_msg
    )

def create_authorization_error(message: str = "Access denied", user_message: str = None) -> AuthorizationError:
    """Create an authorization error"""
    user_msg = user_message or "You don't have permission to perform this action"

    return AuthorizationError(
        message=message,
        user_message=user_msg
    )

def create_business_logic_error(message: str, rule: str = None, user_message: str = None) -> BusinessLogicError:
    """Create a business logic error"""
    user_msg = user_message or message

    return BusinessLogicError(
        message=message,
        rule=rule,
        user_message=user_msg
    )

def create_rate_limit_error(message: str = "Too many requests", user_message: str = None) -> RateLimitError:
    """Create a rate limit error"""
    user_msg = user_message or "You're making requests too quickly. Please wait a moment and try again."

    return RateLimitError(
        message=message,
        user_message=user_msg
    )

def create_system_error(message: str = "System error occurred", user_message: str = None) -> SystemError:
    """Create a system error"""
    user_msg = user_message or "Something went wrong on our end. Please try again later."

    return SystemError(
        message=message,
        user_message=user_msg
    )

# Common error patterns for forms

def create_email_validation_error(email: str = None) -> ValidationError:
    """Create email validation error"""
    message = "Invalid email format"
    if email:
        message = f"'{email}' is not a valid email address"

    return create_field_validation_error(
        field="email",
        message=message,
        code="VALIDATION_EMAIL_001",
        user_message="Please enter a valid email address (e.g., user@domain.com)"
    )

def create_password_validation_error(password: str = None) -> ValidationError:
    """Create password validation error"""
    message = "Invalid password"
    if password:
        if len(password) < 8:
            message = "Password must be at least 8 characters long"
        elif not any(char.isdigit() for char in password):
            message = "Password must contain at least one number"
        elif not any(char.isupper() for char in password):
            message = "Password must contain at least one uppercase letter"

    return create_field_validation_error(
        field="password",
        message=message,
        code="VALIDATION_PASSWORD_001",
        user_message="Password must be at least 8 characters with uppercase, lowercase, and numbers"
    )

def create_required_field_error(field: str) -> ValidationError:
    """Create required field error"""
    return create_field_validation_error(
        field=field,
        message=f"{field.title()} is required",
        code=f"VALIDATION_{field.upper()}_REQUIRED",
        user_message=f"Please enter your {field}"
    )

# Error response formatters for different scenarios

def format_success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """Format a successful response"""
    response = {
        "success": True,
        "message": message
    }

    if data is not None:
        response["data"] = data

    return response

def format_error_response(error: Exception, request_path: str = None, request_method: str = None) -> Dict[str, Any]:
    """Format any exception as a frontend-friendly error response"""
    if hasattr(error, 'to_frontend_dict'):
        return error.to_frontend_dict(request_path, request_method)
    else:
        # Handle non-custom exceptions
        system_error = create_system_error(str(error))
        return system_error.to_frontend_dict(request_path, request_method)

# Validation helper for common patterns

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[ValidationError]:
    """Validate that required fields are present and not empty"""
    errors = []

    for field in required_fields:
        value = data.get(field, "").strip()
        if not value:
            errors.append(create_required_field_error(field))

    return errors

def validate_email_format(email: str) -> Optional[ValidationError]:
    """Validate email format"""
    if not email:
        return create_required_field_error("email")

    # Basic email regex
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        return create_email_validation_error(email)

    return None

def validate_password_strength(password: str) -> Optional[ValidationError]:
    """Validate password strength"""
    if not password:
        return create_required_field_error("password")

    if len(password) < 8:
        return create_password_validation_error(password)

    return None
