"""
Enhanced JWT Security Manager
"""
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REDIS_URL
import redis
import logging

logger = logging.getLogger(__name__)

class JWTSecurityManager:
    def __init__(self):
        if REDIS_URL and REDIS_URL.startswith(('redis://', 'rediss://', 'unix://')):
            self.redis_client = redis.from_url(REDIS_URL)
        else:
            self.redis_client = None
        self.blacklisted_tokens = set()
    
    def create_token(self, user_id: str, additional_claims: dict = None) -> str:
        """Create JWT with enhanced security"""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "jti": f"{user_id}_{int(now.timestamp())}",  # JWT ID for tracking
            "type": "access"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str) -> dict:
        """Verify JWT with additional security checks"""
        try:
            # Check if token is blacklisted
            if self.is_token_blacklisted(token):
                logger.warning("Token found in blacklist")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )

            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            # Additional security checks
            if payload.get("type") != "access":
                logger.warning(f"Invalid token type: {payload.get('type')}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            # Check if token has expired
            exp = payload.get("exp")
            if exp:
                from datetime import datetime
                if datetime.utcnow().timestamp() > exp:
                    logger.warning("Token has expired")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has expired"
                    )

            logger.debug(f"Token verified successfully for user: {payload.get('sub')}")
            return payload

        except JWTError as e:
            logger.warning(f"JWT decode error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    def blacklist_token(self, token: str):
        """Add token to blacklist"""
        if self.redis_client:
            # Store in Redis with expiration
            self.redis_client.setex(f"blacklist:{token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
        else:
            self.blacklisted_tokens.add(token)
    
    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted"""
        if self.redis_client:
            return self.redis_client.exists(f"blacklist:{token}")
        return token in self.blacklisted_tokens
    
    def get_user_from_token(self, token: str) -> str:
        """Extract user ID from token"""
        payload = self.verify_token(token)
        return payload.get("sub")

# Global instance
jwt_security_manager = JWTSecurityManager()
