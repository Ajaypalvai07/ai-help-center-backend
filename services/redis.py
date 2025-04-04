from redis.asyncio import Redis
from typing import Optional, Any, Union
import json
from ..core.config import settings

class RedisService:
    def __init__(self):
        self.redis: Optional[Redis] = None

    async def connect(self):
        self.redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True
        )
        # Test connection
        await self.redis.ping()

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def set_key(self, key: str, value: Any, expire: int = None) -> bool:
        """Set a key with optional expiration time"""
        try:
            value_str = json.dumps(value) if not isinstance(value, (str, int, float)) else str(value)
            await self.redis.set(key, value_str, ex=expire)
            return True
        except Exception:
            return False

    async def get_key(self, key: str) -> Optional[Any]:
        """Get a key's value"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception:
            return None

    async def delete_key(self, key: str) -> bool:
        """Delete a key"""
        try:
            return bool(await self.redis.delete(key))
        except Exception:
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter"""
        try:
            return await self.redis.incrby(key, amount)
        except Exception:
            return None

    # Rate limiting methods
    async def check_rate_limit(self, key: str, limit: int, period: int) -> bool:
        """
        Check if the rate limit has been exceeded
        Returns True if within limit, False if exceeded
        """
        try:
            current = await self.redis.get(key)
            if not current:
                await self.redis.setex(key, period, 1)
                return True
            
            count = int(current)
            if count >= limit:
                return False
            
            await self.redis.incr(key)
            return True
        except Exception:
            return True  # Fail open if Redis is down

    # Caching methods
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a value from cache"""
        return await self.get_key(f"cache:{key}")

    async def cache_set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set a value in cache with optional expiration"""
        if expire is None:
            expire = settings.CACHE_TTL
        return await self.set_key(f"cache:{key}", value, expire)

    async def cache_delete(self, key: str) -> bool:
        """Delete a value from cache"""
        return await self.delete_key(f"cache:{key}")

    # Session methods
    async def set_session(self, session_id: str, data: dict, expire: int = None) -> bool:
        """Store session data"""
        if expire is None:
            expire = settings.SESSION_TTL
        return await self.set_key(f"session:{session_id}", data, expire)

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session data"""
        return await self.get_key(f"session:{session_id}")

    async def delete_session(self, session_id: str) -> bool:
        """Delete session data"""
        return await self.delete_key(f"session:{session_id}")

redis_client = RedisService() 