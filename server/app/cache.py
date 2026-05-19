"""Redis cache helpers."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import orjson
import redis.asyncio as redis

from app.config import settings

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """单例 Redis 连接。"""
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            settings.REDIS_URL,
            decode_responses=False,
            health_check_interval=30,
        )
    return _redis


async def cache_get_or_set(
    key: str,
    factory: Callable[[], Awaitable[Any]],
    ttl: int,
) -> Any:
    """读缓存；未命中则调 factory() 并写入。"""
    r = get_redis()
    try:
        cached = await r.get(key)
        if cached:
            return orjson.loads(cached)
    except Exception:
        # Redis 故障不影响业务，降级直读
        return await factory()

    fresh = await factory()
    try:
        await r.set(key, orjson.dumps(fresh, default=str), ex=ttl)
    except Exception:
        pass
    return fresh


async def cache_invalidate(prefix: str) -> int:
    """按 key 前缀批量删除（用于物化视图刷新后）。"""
    r = get_redis()
    n = 0
    async for k in r.scan_iter(match=f"{prefix}*", count=200):
        await r.delete(k)
        n += 1
    return n


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
