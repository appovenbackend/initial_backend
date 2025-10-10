from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
import hmac
import hashlib
import secrets
import time
from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hash password with proper length validation and security measures.

    Args:
        password: Plain text password to hash

    Returns:
        str: Hashed password

    Raises:
        ValueError: If password is too long or empty
    """
    if not password:
        raise ValueError("Password cannot be empty")

    # bcrypt has a 72-byte limit, but we should enforce reasonable password limits
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        raise ValueError("Password is too long (maximum 72 characters)")

    if len(password_bytes) < 8:
        raise ValueError("Password is too short (minimum 8 characters)")

    return pwd.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify password with constant-time comparison to prevent timing attacks.

    Args:
        plain: Plain text password to verify
        hashed: Hashed password from database

    Returns:
        bool: True if password matches, False otherwise
    """
    if not plain or not hashed:
        return False

    # Validate password length before verification
    if len(plain.encode('utf-8')) > 72:
        return False

    # Use constant-time comparison to prevent timing attacks
    # Passlib's verify is designed to be relatively constant-time
    return pwd.verify(plain, hashed)

def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        bool: True if strings are equal
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)

    return result == 0

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        length: Length of token in bytes

    Returns:
        str: Secure random token
    """
    return secrets.token_urlsafe(length)

def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.

    Args:
        token: Token to hash

    Returns:
        str: Hashed token
    """
    # Use SHA-256 for token hashing
    return hashlib.sha256(token.encode()).hexdigest()

def verify_token(plain_token: str, hashed_token: str) -> bool:
    """
    Verify a token using constant-time comparison.

    Args:
        plain_token: Plain token
        hashed_token: Hashed token from database

    Returns:
        bool: True if token matches
    """
    if not plain_token or not hashed_token:
        return False

    expected_hash = hash_token(plain_token)
    return constant_time_compare(expected_hash, hashed_token)

def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=(expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": subject, "exp": int(exp.timestamp())}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data
    except JWTError as e:
        raise
