"""Redis cache service."""
import json
from typing import Optional, Any
import redis.asyncio as redis
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


class CacheService:
    """Redis-based caching service."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[redis.Redis] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            self._client = redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._client.ping()
            self._connected = True
            logger.info("Redis connected")
            return True
        except Exception as e:
            logger.warning("Redis connection failed, running without cache", error=str(e))
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._connected:
            return None
        
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Cache get failed", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache."""
        if not self._connected:
            return False
        
        try:
            ttl = ttl or self.settings.cache_ttl
            await self._client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._connected:
            return False
        
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed", key=key, error=str(e))
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self._connected:
            return 0
        
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                await self._client.delete(*keys)
            
            return len(keys)
        except Exception as e:
            logger.warning("Cache clear failed", pattern=pattern, error=str(e))
            return 0
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected


# Global cache instance
cache = CacheService()
