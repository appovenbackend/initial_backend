"""
Input Validation and Sanitization System
Provides comprehensive input validation and sanitization for all user inputs
"""
import re
import html
import bleach
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, validator, Field
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

class InputValidator:
    """Comprehensive input validation and sanitization"""
    
    # Regex patterns for validation
    PHONE_PATTERN = re.compile(r'^\+?[1-9]\d{1,14}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
    EVENT_ID_PATTERN = re.compile(r'^evt_[a-f0-9]{10}$')
    USER_ID_PATTERN = re.compile(r'^u_[a-f0-9]{10}$')
    TICKET_ID_PATTERN = re.compile(r'^tkt_[a-f0-9]{10}$')
    ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,!?]+$')
    
    # Allowed HTML tags for rich text
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    
    # Maximum lengths
    MAX_NAME_LENGTH = 100
    MAX_EMAIL_LENGTH = 254
    MAX_PHONE_LENGTH = 15
    MAX_BIO_LENGTH = 500
    MAX_EVENT_TITLE_LENGTH = 200
    MAX_EVENT_DESCRIPTION_LENGTH = 2000
    MAX_VENUE_LENGTH = 200
    MAX_CITY_LENGTH = 100
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validate phone number format"""
        if not phone or not isinstance(phone, str):
            return False
        return bool(InputValidator.PHONE_PATTERN.match(phone.strip()))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False
        return bool(InputValidator.EMAIL_PATTERN.match(email.strip().lower()))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username or not isinstance(username, str):
            return False
        return bool(InputValidator.USERNAME_PATTERN.match(username.strip()))
    
    @staticmethod
    def validate_event_id(event_id: str) -> bool:
        """Validate event ID format"""
        if not event_id or not isinstance(event_id, str):
            return False
        return bool(InputValidator.EVENT_ID_PATTERN.match(event_id.strip()))
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate user ID format"""
        if not user_id or not isinstance(user_id, str):
            return False
        return bool(InputValidator.USER_ID_PATTERN.match(user_id.strip()))
    
    @staticmethod
    def validate_ticket_id(ticket_id: str) -> bool:
        """Validate ticket ID format"""
        if not ticket_id or not isinstance(ticket_id, str):
            return False
        return bool(InputValidator.TICKET_ID_PATTERN.match(ticket_id.strip()))
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = None, allow_html: bool = False) -> str:
        """Sanitize text input"""
        if not text or not isinstance(text, str):
            return ""
        
        # Strip whitespace
        text = text.strip()
        
        # Truncate if too long
        if max_length and len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Text truncated to {max_length} characters")
        
        if allow_html:
            # Allow only safe HTML tags
            text = bleach.clean(text, tags=InputValidator.ALLOWED_TAGS, strip=True)
        else:
            # Escape HTML entities
            text = html.escape(text)
        
        return text
    
    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitize name input"""
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name is required"
            )
        
        name = InputValidator.sanitize_text(name, InputValidator.MAX_NAME_LENGTH)
        
        if len(name) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name must be at least 2 characters long"
            )
        
        if not InputValidator.ALPHANUMERIC_PATTERN.match(name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Name contains invalid characters"
            )
        
        return name
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """Sanitize email input"""
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )
        
        email = email.strip().lower()
        
        if len(email) > InputValidator.MAX_EMAIL_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is too long"
            )
        
        if not InputValidator.validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        return email
    
    @staticmethod
    def sanitize_phone(phone: str) -> str:
        """Sanitize phone number input"""
        if not phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required"
            )
        
        phone = phone.strip()
        
        if len(phone) > InputValidator.MAX_PHONE_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is too long"
            )
        
        if not InputValidator.validate_phone_number(phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format"
            )
        
        return phone
    
    @staticmethod
    def sanitize_bio(bio: str) -> str:
        """Sanitize bio input"""
        if not bio:
            return ""
        
        bio = InputValidator.sanitize_text(bio, InputValidator.MAX_BIO_LENGTH, allow_html=True)
        return bio
    
    @staticmethod
    def sanitize_event_title(title: str) -> str:
        """Sanitize event title input"""
        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event title is required"
            )
        
        title = InputValidator.sanitize_text(title, InputValidator.MAX_EVENT_TITLE_LENGTH)
        
        if len(title) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event title must be at least 3 characters long"
            )
        
        return title
    
    @staticmethod
    def sanitize_event_description(description: str) -> str:
        """Sanitize event description input"""
        if not description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event description is required"
            )
        
        description = InputValidator.sanitize_text(description, InputValidator.MAX_EVENT_DESCRIPTION_LENGTH, allow_html=True)
        
        if len(description) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event description must be at least 10 characters long"
            )
        
        return description
    
    @staticmethod
    def sanitize_venue(venue: str) -> str:
        """Sanitize venue input"""
        if not venue:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Venue is required"
            )
        
        venue = InputValidator.sanitize_text(venue, InputValidator.MAX_VENUE_LENGTH)
        
        if len(venue) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Venue must be at least 3 characters long"
            )
        
        return venue
    
    @staticmethod
    def sanitize_city(city: str) -> str:
        """Sanitize city input"""
        if not city:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="City is required"
            )
        
        city = InputValidator.sanitize_text(city, InputValidator.MAX_CITY_LENGTH)
        
        if len(city) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="City must be at least 2 characters long"
            )
        
        return city
    
    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize URL input"""
        if not url:
            return ""
        
        url = url.strip()
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Validate URL format
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format"
            )
        
        return url
    
    @staticmethod
    def validate_price(price: int) -> int:
        """Validate price input"""
        if not isinstance(price, int):
            try:
                price = int(price)
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Price must be a valid integer"
                )
        
        if price < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price cannot be negative"
            )
        
        if price > 1000000:  # 10 lakh rupees
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price is too high"
            )
        
        return price
    
    @staticmethod
    def validate_datetime(dt_string: str) -> str:
        """Validate datetime string"""
        if not dt_string:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="DateTime is required"
            )
        
        try:
            from dateutil import parser
            dt = parser.isoparse(dt_string)
            
            # Check if datetime is in the future
            from datetime import datetime, timezone
            if dt < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="DateTime must be in the future"
                )
            
            return dt_string
            
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid datetime format"
            )

# Global input validator instance
input_validator = InputValidator()

# Convenience functions
def validate_phone_number(phone: str) -> bool:
    return input_validator.validate_phone_number(phone)

def validate_email(email: str) -> bool:
    return input_validator.validate_email(email)

def validate_event_id(event_id: str) -> bool:
    return input_validator.validate_event_id(event_id)

def sanitize_text(text: str, max_length: int = None, allow_html: bool = False) -> str:
    return input_validator.sanitize_text(text, max_length, allow_html)

def sanitize_name(name: str) -> str:
    return input_validator.sanitize_name(name)

def sanitize_email(email: str) -> str:
    return input_validator.sanitize_email(email)

def sanitize_phone(phone: str) -> str:
    return input_validator.sanitize_phone(phone)
