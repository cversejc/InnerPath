import redis.asyncio as redis
from typing import Optional, Any
import json
from app.config import settings

# Redis client for caching
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    return redis_client


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()


async def get_redis() -> redis.Redis:
    """Get Redis client"""
    if redis_client is None:
        await init_redis()
    return redis_client


async def cache_set(key: str, value: Any, expire: int = 300):
    """Set cache with expiration (default 5 minutes)"""
    client = await get_redis()
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    await client.setex(key, expire, value)


async def cache_get(key: str) -> Optional[str]:
    """Get cache value"""
    client = await get_redis()
    value = await client.get(key)
    return value


async def cache_delete(key: str):
    """Delete cache key"""
    client = await get_redis()
    await client.delete(key)


async def cache_exists(key: str) -> bool:
    """Check if cache key exists"""
    client = await get_redis()
    return await client.exists(key) > 0
