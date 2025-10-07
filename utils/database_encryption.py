"""
Database Encryption Utilities
Provides encryption/decryption for sensitive data stored in database
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Any, Dict, Optional
import logging
import json

logger = logging.getLogger(__name__)

class DatabaseEncryption:
    """Database encryption utility for sensitive data"""
    
    def __init__(self):
        self._key = self._get_or_create_key()
        self._fernet = Fernet(self._key)
    
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key"""
        # Try to get key from environment variable
        key_str = os.getenv("ENCRYPTION_KEY")
        
        if key_str:
            try:
                return base64.urlsafe_b64decode(key_str.encode())
            except Exception as e:
                logger.error(f"Invalid encryption key format: {e}")
        
        # Generate new key if not found
        logger.warning("No encryption key found, generating new key")
        key = Fernet.generate_key()
        
        # Log the key for manual setup (in production, this should be set via environment)
        key_str = base64.urlsafe_b64encode(key).decode()
        logger.warning(f"Generated new encryption key. Set ENCRYPTION_KEY={key_str} in your environment")
        
        return key
    
    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string"""
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt string: {e}")
            raise
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """Decrypt a string"""
        if not encrypted_text:
            return ""
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt string: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt a dictionary"""
        if not data:
            return ""
        
        try:
            json_str = json.dumps(data)
            return self.encrypt_string(json_str)
        except Exception as e:
            logger.error(f"Failed to encrypt dict: {e}")
            raise
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt a dictionary"""
        if not encrypted_data:
            return {}
        
        try:
            json_str = self.decrypt_string(encrypted_data)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to decrypt dict: {e}")
            raise
    
    def encrypt_sensitive_fields(self, data: Dict[str, Any], 
                                sensitive_fields: list = None) -> Dict[str, Any]:
        """Encrypt sensitive fields in a dictionary"""
        if sensitive_fields is None:
            sensitive_fields = ["password", "phone", "email", "credit_card", "ssn"]
        
        encrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                try:
                    encrypted_data[field] = self.encrypt_string(str(encrypted_data[field]))
                except Exception as e:
                    logger.error(f"Failed to encrypt field {field}: {e}")
                    # Keep original value if encryption fails
                    pass
        
        return encrypted_data
    
    def decrypt_sensitive_fields(self, data: Dict[str, Any], 
                                sensitive_fields: list = None) -> Dict[str, Any]:
        """Decrypt sensitive fields in a dictionary"""
        if sensitive_fields is None:
            sensitive_fields = ["password", "phone", "email", "credit_card", "ssn"]
        
        decrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt_string(str(decrypted_data[field]))
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field}: {e}")
                    # Keep encrypted value if decryption fails
                    pass
        
        return decrypted_data

class SecureDataManager:
    """Manager for secure data operations"""
    
    def __init__(self):
        self.encryption = DatabaseEncryption()
    
    def secure_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Secure user data before storing in database"""
        sensitive_fields = ["password", "phone", "email"]
        return self.encryption.encrypt_sensitive_fields(user_data, sensitive_fields)
    
    def unsecure_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Unsecure user data after retrieving from database"""
        sensitive_fields = ["password", "phone", "email"]
        return self.encryption.decrypt_sensitive_fields(user_data, sensitive_fields)
    
    def secure_payment_data(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Secure payment data before storing in database"""
        sensitive_fields = ["razorpay_payment_id", "razorpay_signature", "email", "contact"]
        return self.encryption.encrypt_sensitive_fields(payment_data, sensitive_fields)
    
    def unsecure_payment_data(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Unsecure payment data after retrieving from database"""
        sensitive_fields = ["razorpay_payment_id", "razorpay_signature", "email", "contact"]
        return self.encryption.decrypt_sensitive_fields(payment_data, sensitive_fields)
    
    def secure_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Secure event data (if needed)"""
        # Events typically don't have sensitive data, but this can be extended
        return event_data
    
    def unsecure_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Unsecure event data (if needed)"""
        return event_data

class PasswordManager:
    """Secure password management"""
    
    def __init__(self):
        self.encryption = DatabaseEncryption()
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Truncate password if too long (bcrypt limit is 72 bytes)
        if len(password.encode('utf-8')) > 72:
            password_bytes = password.encode('utf-8')[:72]
            password = password_bytes.decode('utf-8', errors='ignore')
        
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Truncate password if too long
        if len(plain_password.encode('utf-8')) > 72:
            password_bytes = plain_password.encode('utf-8')[:72]
            plain_password = password_bytes.decode('utf-8', errors='ignore')
        
        return pwd_context.verify(plain_password, hashed_password)
    
    def encrypt_password(self, password: str) -> str:
        """Encrypt password for storage (additional layer)"""
        return self.encryption.encrypt_string(password)
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt password (for verification purposes)"""
        return self.encryption.decrypt_string(encrypted_password)

class DataMasking:
    """Data masking utilities for logging and debugging"""
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address"""
        if not email or "@" not in email:
            return email
        
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            return f"{local[0]}***@{domain}"
        
        return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number"""
        if not phone or len(phone) < 4:
            return phone
        
        return f"{phone[:2]}{'*' * (len(phone) - 4)}{phone[-2:]}"
    
    @staticmethod
    def mask_credit_card(card_number: str) -> str:
        """Mask credit card number"""
        if not card_number or len(card_number) < 8:
            return card_number
        
        return f"{card_number[:4]}{'*' * (len(card_number) - 8)}{card_number[-4:]}"
    
    @staticmethod
    def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in dictionary"""
        masked_data = data.copy()
        
        # Mask common sensitive fields
        if "email" in masked_data:
            masked_data["email"] = DataMasking.mask_email(str(masked_data["email"]))
        
        if "phone" in masked_data:
            masked_data["phone"] = DataMasking.mask_phone(str(masked_data["phone"]))
        
        if "password" in masked_data:
            masked_data["password"] = "***"
        
        if "credit_card" in masked_data:
            masked_data["credit_card"] = DataMasking.mask_credit_card(str(masked_data["credit_card"]))
        
        return masked_data

# Global instances
db_encryption = DatabaseEncryption()
secure_data_manager = SecureDataManager()
password_manager = PasswordManager()
data_masking = DataMasking()

# Convenience functions
def encrypt_string(plaintext: str) -> str:
    """Encrypt a string"""
    return db_encryption.encrypt_string(plaintext)

def decrypt_string(encrypted_text: str) -> str:
    """Decrypt a string"""
    return db_encryption.decrypt_string(encrypted_text)

def encrypt_dict(data: Dict[str, Any]) -> str:
    """Encrypt a dictionary"""
    return db_encryption.encrypt_dict(data)

def decrypt_dict(encrypted_data: str) -> Dict[str, Any]:
    """Decrypt a dictionary"""
    return db_encryption.decrypt_dict(encrypted_data)

def secure_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Secure user data before storing in database"""
    return secure_data_manager.secure_user_data(user_data)

def unsecure_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Unsecure user data after retrieving from database"""
    return secure_data_manager.unsecure_user_data(user_data)

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return password_manager.hash_password(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return password_manager.verify_password(plain_password, hashed_password)

def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive data in dictionary"""
    return data_masking.mask_sensitive_data(data)
