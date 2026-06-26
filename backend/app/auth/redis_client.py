"""Async Redis client for auth operations (refresh token blacklist)."""

from __future__ import annotations

import logging

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)


async def get_redis() -> Redis:
    """Return an async Redis connection."""
    return Redis.from_url(settings.redis_url, decode_responses=True)


async def blacklist_refresh_token(user_id: str, refresh_token: str, ttl_seconds: int = 604800) -> None:
    """Add a refresh token to the user's blacklist set.

    The set has a TTL equal to the refresh token lifetime (default 7 days).
    """
    r = await get_redis()
    key = f"refresh_blacklist:{user_id}"
    await r.sadd(key, refresh_token)
    await r.expire(key, ttl_seconds)
    await r.aclose()


async def is_token_blacklisted(user_id: str, refresh_token: str) -> bool:
    """Check if a refresh token is blacklisted."""
    r = await get_redis()
    key = f"refresh_blacklist:{user_id}"
    result = await r.sismember(key, refresh_token)
    await r.aclose()
    return bool(result)


async def clear_user_blacklist(user_id: str) -> None:
    """Delete the entire blacklist set for a user (theft detected)."""
    r = await get_redis()
    key = f"refresh_blacklist:{user_id}"
    await r.delete(key)
    await r.aclose()
