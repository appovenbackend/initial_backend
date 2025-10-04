"""
SQL Injection Protection and Input Sanitization
"""
import re
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)

class SQLInjectionProtection:
    """Additional SQL injection protection beyond ORM"""
    
    DANGEROUS_PATTERNS = [
        r'(union|select|insert|update|delete|drop|create|alter|exec|execute)',
        r'(script|javascript|vbscript|onload|onerror)',
        r'(<|>|&lt;|&gt;|&#x3C;|&#x3E;)',
        r'(chr|char|ascii|substring|len|length)',
        r'(xp_|sp_|fn_)',  # SQL Server procedures
        r'(benchmark|sleep|waitfor|delay)',  # Time-based attacks
        r'(or\s+1\s*=\s*1|and\s+1\s*=\s*1)',  # Common SQL injection patterns
        r'(union\s+select|union\s+all\s+select)',  # Union-based attacks
        r'(information_schema|sys\.|pg_|mysql\.)',  # Database schema attacks
    ]
    
    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return value
            
        original_value = value
        
        # Remove dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
            
        # Log if sanitization occurred
        if value != original_value:
            logger.warning(f"Input sanitized: '{original_value}' -> '{value}'")
            
        # Limit length
        return value[:1000]
    
    @classmethod
    def validate_input(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize input data"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.validate_input(value)
            elif isinstance(value, list):
                sanitized[key] = [cls.sanitize_string(item) if isinstance(item, str) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized
    
    @classmethod
    def is_safe_input(cls, value: str) -> bool:
        """Check if input contains dangerous patterns"""
        if not isinstance(value, str):
            return True
            
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Potentially dangerous input detected: '{value}'")
                return False
        return True

class InputValidator:
    """General input validation utilities"""
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validate phone number format"""
        pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        pattern = r'^https?://.+'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def validate_event_id(event_id: str) -> bool:
        """Validate event ID format"""
        pattern = r'^evt_[a-f0-9]{10}$'
        return bool(re.match(pattern, event_id))
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate user ID format"""
        pattern = r'^u_[a-f0-9]{10}$'
        return bool(re.match(pattern, user_id))
    
    @staticmethod
    def validate_ticket_id(ticket_id: str) -> bool:
        """Validate ticket ID format"""
        pattern = r'^t_[a-f0-9]{10}$'
        return bool(re.match(pattern, ticket_id))
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Limit length
        filename = filename[:100]
        # Ensure it's not empty
        if not filename:
            filename = "file"
        return filename

# Global instances
sql_protection = SQLInjectionProtection()
input_validator = InputValidator()
