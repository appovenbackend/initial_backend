"""
Role-Based Access Control
"""
from enum import Enum
from functools import wraps
from fastapi import HTTPException, status, Request
from core.jwt_security import jwt_security_manager
import logging

logger = logging.getLogger(__name__)

class UserRole(Enum):
    USER = "user"
    ORGANIZER = "organizer"
    ADMIN = "admin"

def get_current_user_role(request: Request) -> str:
    """Extract user role from JWT token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return UserRole.USER.value
    
    try:
        token = auth_header.split(" ")[1]
        payload = jwt_security_manager.verify_token(token)
        return payload.get("role", UserRole.USER.value)
    except:
        return UserRole.USER.value

def get_current_user_id(request: Request) -> str:
    """Extract user ID from JWT token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    try:
        token = auth_header.split(" ")[1]
        return jwt_security_manager.get_user_from_token(token)
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_role(required_role: UserRole):
    """Decorator to require specific role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for key, value in kwargs.items():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Request not found")
            
            # Get user role from JWT
            user_role = get_current_user_role(request)
            
            # Check role hierarchy
            role_hierarchy = {
                UserRole.USER.value: 1,
                UserRole.ORGANIZER.value: 2,
                UserRole.ADMIN.value: 3
            }
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role.value, 0):
                logger.warning(f"Access denied: User role {user_role} < required {required_role.value}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires {required_role.value} role or higher"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_authenticated(func):
    """Decorator to require authentication"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request from kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                    break
        
        if not request:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Request not found")
        
        # Check authentication
        try:
            get_current_user_id(request)
        except HTTPException:
            raise
        
        return await func(*args, **kwargs)
    return wrapper

# Convenience functions
def is_admin(request: Request) -> bool:
    """Check if current user is admin"""
    return get_current_user_role(request) == UserRole.ADMIN.value

def is_organizer(request: Request) -> bool:
    """Check if current user is organizer or admin"""
    role = get_current_user_role(request)
    return role in [UserRole.ORGANIZER.value, UserRole.ADMIN.value]

def is_authenticated(request: Request) -> bool:
    """Check if user is authenticated"""
    try:
        get_current_user_id(request)
        return True
    except:
        return False

def get_current_user(request: Request) -> str:
    """Extract user ID from JWT token (alias for get_current_user_id)"""
    return get_current_user_id(request)
