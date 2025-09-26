import redis
import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta
import logging
from core.config import REDIS_URL, REDIS_PASSWORD, REDIS_DB

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = None
        self._connect()

    def _connect(self):
        """Connect to Redis server.
        Supports REDIS_URL as either 'host:port' or full 'redis://[:password@]host:port/db'.
        """
        try:
            if not REDIS_URL:
                logger.warning("Redis URL not configured, using in-memory cache")
                self.redis_client = None
                return

            if '://' in REDIS_URL:
                # Full URL provided (e.g., redis://default:pass@host:port/0)
                self.redis_client = redis.from_url(
                    REDIS_URL,
                    password=REDIS_PASSWORD or None,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    health_check_interval=30
                )
            else:
                host = REDIS_URL.split(':')[0]
                port = int(REDIS_URL.split(':')[1]) if ':' in REDIS_URL else 6379
                self.redis_client = redis.Redis(
                    host=host,
                    port=port,
                    password=REDIS_PASSWORD,
                    db=REDIS_DB or 0,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )

            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.redis_client:
                # Try Redis first
                value = self.redis_client.get(key)
                if value:
                    # Try to deserialize JSON
                    try:
                        return json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        return value
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)

            if self.redis_client:
                # Use Redis
                if ttl_seconds:
                    return bool(self.redis_client.setex(key, ttl_seconds, serialized_value))
                else:
                    return bool(self.redis_client.set(key, serialized_value))
            else:
                # In-memory fallback (would need to implement)
                logger.warning("Redis not available, using in-memory cache")
                return False
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            return False
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.exists(key))
            return False
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    def expire(self, key: str, ttl_seconds: int) -> bool:
        """Set expiration time for key"""
        try:
            if self.redis_client:
                return bool(self.redis_client.expire(key, ttl_seconds))
            return False
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache"""
        try:
            if self.redis_client:
                return self.redis_client.incr(key, amount)
            return None
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None

    def get_or_set(self, key: str, default_value_func, ttl_seconds: Optional[int] = None):
        """Get value from cache or set default if not exists"""
        value = self.get(key)
        if value is None:
            value = default_value_func()
            self.set(key, value, ttl_seconds)
        return value

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error for pattern {pattern}: {e}")
            return 0

    def get_stats(self) -> dict:
        """Get cache statistics"""
        try:
            if self.redis_client:
                info = self.redis_client.info()
                return {
                    'connected': True,
                    'total_connections': info.get('total_connections_received', 0),
                    'memory_used': info.get('used_memory_human', '0B'),
                    'uptime_days': info.get('uptime_in_days', 0),
                    'connected_clients': info.get('connected_clients', 0),
                    'keys': self.redis_client.dbsize()
                }
            else:
                return {'connected': False, 'error': 'Redis not available'}
        except Exception as e:
            return {'connected': False, 'error': str(e)}

    def health_check(self) -> bool:
        """Check if cache is healthy"""
        try:
            if self.redis_client:
                self.redis_client.ping()
                return True
            return False
        except Exception:
            return False

# Global cache service instance
cache_service = CacheService()

# Convenience functions
def get_cache(key: str) -> Optional[Any]:
    return cache_service.get(key)

def set_cache(key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
    return cache_service.set(key, value, ttl_seconds)

def delete_cache(key: str) -> bool:
    return cache_service.delete(key)

def cache_exists(key: str) -> bool:
    return cache_service.exists(key)

def clear_cache_pattern(pattern: str) -> int:
    return cache_service.clear_pattern(pattern)

def get_cache_stats() -> dict:
    return cache_service.get_stats()

def is_cache_healthy() -> bool:
    return cache_service.health_check()
