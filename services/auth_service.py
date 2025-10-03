import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from functools import wraps
from fastapi import HTTPException, Request
from utils.database import read_users, get_database_session
from services.audit_service import audit_service, AuditSeverity
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User role definitions"""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"

class Permission(Enum):
    """Permission definitions"""
    # User permissions
    READ_OWN_PROFILE = "read_own_profile"
    UPDATE_OWN_PROFILE = "update_own_profile"
    DELETE_OWN_ACCOUNT = "delete_own_account"

    # Social permissions
    SEND_CONNECTION_REQUEST = "send_connection_request"
    ACCEPT_CONNECTION_REQUEST = "accept_connection_request"
    VIEW_CONNECTIONS = "view_connections"
    VIEW_SOCIAL_FEED = "view_social_feed"

    # Event permissions
    CREATE_EVENT = "create_event"
    READ_EVENTS = "read_events"
    UPDATE_EVENT = "update_event"
    DELETE_EVENT = "delete_event"

    # Payment permissions
    CREATE_PAYMENT = "create_payment"
    PROCESS_PAYMENT = "process_payment"

    # Admin permissions
    MANAGE_USERS = "manage_users"
    MANAGE_EVENTS = "manage_events"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    SEND_BULK_NOTIFICATIONS = "send_bulk_notifications"
    MANAGE_CACHE = "manage_cache"
    VIEW_ANALYTICS = "view_analytics"

# Role-based permissions mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.READ_OWN_PROFILE,
        Permission.UPDATE_OWN_PROFILE,
        Permission.DELETE_OWN_ACCOUNT,
        Permission.SEND_CONNECTION_REQUEST,
        Permission.ACCEPT_CONNECTION_REQUEST,
        Permission.VIEW_CONNECTIONS,
        Permission.VIEW_SOCIAL_FEED,
        Permission.CREATE_EVENT,
        Permission.READ_EVENTS,
        Permission.UPDATE_EVENT,
        Permission.DELETE_EVENT,
        Permission.CREATE_PAYMENT,
        Permission.PROCESS_PAYMENT,
        Permission.MANAGE_USERS,
        Permission.MANAGE_EVENTS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.SEND_BULK_NOTIFICATIONS,
        Permission.MANAGE_CACHE,
        Permission.VIEW_ANALYTICS,
    ],
    UserRole.MODERATOR: [
        Permission.READ_OWN_PROFILE,
        Permission.UPDATE_OWN_PROFILE,
        Permission.DELETE_OWN_ACCOUNT,
        Permission.SEND_CONNECTION_REQUEST,
        Permission.ACCEPT_CONNECTION_REQUEST,
        Permission.VIEW_CONNECTIONS,
        Permission.VIEW_SOCIAL_FEED,
        Permission.CREATE_EVENT,
        Permission.READ_EVENTS,
        Permission.UPDATE_EVENT,
        Permission.CREATE_PAYMENT,
        Permission.PROCESS_PAYMENT,
        Permission.VIEW_AUDIT_LOGS,
        Permission.SEND_BULK_NOTIFICATIONS,
    ],
    UserRole.USER: [
        Permission.READ_OWN_PROFILE,
        Permission.UPDATE_OWN_PROFILE,
        Permission.SEND_CONNECTION_REQUEST,
        Permission.ACCEPT_CONNECTION_REQUEST,
        Permission.VIEW_CONNECTIONS,
        Permission.VIEW_SOCIAL_FEED,
        Permission.READ_EVENTS,
        Permission.CREATE_PAYMENT,
        Permission.PROCESS_PAYMENT,
    ],
    UserRole.GUEST: [
        Permission.READ_EVENTS,
    ]
}

class AuthService:
    """Authentication and authorization service"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_user_role(self, user_id: str) -> UserRole:
        """Get user role from database"""
        try:
            users = read_users()
            user = next((u for u in users if u['id'] == user_id), None)

            if not user:
                return UserRole.GUEST

            role_str = user.get('role', 'user')
            return UserRole(role_str)

        except Exception as e:
            logger.error(f"Error getting user role for {user_id}: {str(e)}")
            return UserRole.GUEST

    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission"""
        user_role = self.get_user_role(user_id)
        role_permissions = ROLE_PERMISSIONS.get(user_role, [])

        return permission in role_permissions

    def require_permission(self, permission: Permission):
        """Decorator to require specific permission"""
        def decorator(func):
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                # Get user ID from request headers
                user_id = request.headers.get("X-User-ID")
                if not user_id:
                    audit_service.log_security_event(
                        "Unauthorized access attempt - missing user ID",
                        AuditSeverity.HIGH,
                        request.client.host if request.client else "unknown",
                        {"endpoint": str(request.url.path), "method": request.method}
                    )
                    raise HTTPException(status_code=401, detail="Authentication required")

                if not self.has_permission(user_id, permission):
                    audit_service.log_security_event(
                        f"Permission denied: {permission.value}",
                        AuditSeverity.MEDIUM,
                        request.client.host if request.client else "unknown",
                        {
                            "user_id": user_id,
                            "permission": permission.value,
                            "endpoint": str(request.url.path),
                            "method": request.method
                        }
                    )
                    raise HTTPException(status_code=403, detail="Insufficient permissions")

                return await func(request, *args, **kwargs)
            return wrapper
        return decorator

    def require_role(self, required_role: UserRole):
        """Decorator to require specific role"""
        def decorator(func):
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                user_id = request.headers.get("X-User-ID")
                if not user_id:
                    audit_service.log_security_event(
                        "Unauthorized access attempt - missing user ID",
                        AuditSeverity.HIGH,
                        request.client.host if request.client else "unknown"
                    )
                    raise HTTPException(status_code=401, detail="Authentication required")

                user_role = self.get_user_role(user_id)
                if user_role != required_role and not self._is_role_higher(user_role, required_role):
                    audit_service.log_security_event(
                        f"Role access denied: required {required_role.value}, has {user_role.value}",
                        AuditSeverity.MEDIUM,
                        request.client.host if request.client else "unknown",
                        {
                            "user_id": user_id,
                            "required_role": required_role.value,
                            "user_role": user_role.value,
                            "endpoint": str(request.url.path)
                        }
                    )
                    raise HTTPException(status_code=403, detail=f"Role {required_role.value} required")

                return await func(request, *args, **kwargs)
            return wrapper
        return decorator

    def _is_role_higher(self, user_role: UserRole, required_role: UserRole) -> bool:
        """Check if user role is higher than or equal to required role"""
        role_hierarchy = {
            UserRole.GUEST: 0,
            UserRole.USER: 1,
            UserRole.MODERATOR: 2,
            UserRole.ADMIN: 3
        }

        return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)

    def validate_input_data(self, data: Dict[str, Any], allowed_fields: List[str], max_length: int = 1000) -> Dict[str, Any]:
        """Validate and sanitize input data"""
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="Invalid input data format")

        # Check for allowed fields only
        sanitized_data = {}
        for field in allowed_fields:
            if field in data:
                value = data[field]

                # Basic type validation and sanitization
                if isinstance(value, str):
                    # Sanitize strings - remove potential script injection
                    sanitized_value = value.strip()
                    if len(sanitized_value) > max_length:
                        raise HTTPException(status_code=400, detail=f"Field {field} exceeds maximum length")
                    sanitized_data[field] = sanitized_value

                elif isinstance(value, (int, float, bool)):
                    sanitized_data[field] = value

                elif isinstance(value, list):
                    # Validate list items
                    if field in ['subscribedEvents']:  # Known list fields
                        sanitized_data[field] = [str(item) for item in value if str(item)]
                    else:
                        sanitized_data[field] = value

                elif value is None:
                    sanitized_data[field] = None

                else:
                    # Convert other types to string
                    sanitized_data[field] = str(value)

        return sanitized_data

    def validate_user_ownership(self, user_id: str, resource_user_id: str, resource_type: str = "resource"):
        """Validate that user owns the resource they're trying to access"""
        if user_id != resource_user_id:
            # Check if user is admin (admins can access any resource)
            if not self.has_permission(user_id, Permission.MANAGE_USERS):
                audit_service.log_security_event(
                    f"Unauthorized {resource_type} access attempt",
                    AuditSeverity.MEDIUM,
                    "unknown",  # IP not available in this context
                    {
                        "user_id": user_id,
                        "target_user_id": resource_user_id,
                        "resource_type": resource_type
                    }
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"Not authorized to access this {resource_type}"
                )

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID with proper error handling"""
        try:
            users = read_users()
            return next((u for u in users if u['id'] == user_id), None)
        except Exception as e:
            logger.error(f"Error retrieving user {user_id}: {str(e)}")
            return None

    def log_user_action(self, user_id: str, action: str, details: Dict[str, Any], ip_address: str = None):
        """Log user action for audit purposes"""
        audit_service.log_data_modification(
            user_id=user_id,
            operation=action,
            table_name="users",
            record_id=user_id,
            ip_address=ip_address or "unknown",
            details=details
        )

# Global auth service instance
auth_service = AuthService()
