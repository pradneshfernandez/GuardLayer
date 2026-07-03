import hashlib
import json
import logging
import os

import redis.asyncio as redis_asyncio
from redis.exceptions import RedisError

from extraction.normalizer import normalize
from voygr.models import VerificationResponse

logger = logging.getLogger(__name__)

_KEY_PREFIX = "guardlayer:verify:"

_pool: redis_asyncio.Redis | None = None
_available: bool | None = None  # None = not yet determined
_hits = 0
_misses = 0
_warned = False


def _ttl_seconds() -> int:
    return int(os.environ.get("CACHE_TTL_SECONDS", "604800"))


def _redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379")


def _cache_key(name: str, address: str) -> str:
    normalized = f"{normalize(name)}|{normalize(address)}"
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"{_KEY_PREFIX}{digest}"


async def _get_connection() -> redis_asyncio.Redis | None:
    global _pool, _available, _warned
    if _available is False:
        return None
    if _pool is None:
        _pool = redis_asyncio.Redis.from_url(_redis_url(), decode_responses=True)
    if _available is None:
        try:
            await _pool.ping()
            _available = True
        except (RedisError, OSError):
            _available = False
            if not _warned:
                logger.warning("Redis unavailable — falling back to no-op cache")
                _warned = True
            return None
    return _pool


async def get(name: str, address: str) -> VerificationResponse | None:
    global _hits, _misses
    conn = await _get_connection()
    if conn is None:
        return None

    key = _cache_key(name, address)
    try:
        raw = await conn.get(key)
    except RedisError:
        return None

    if raw is None:
        _misses += 1
        return None

    _hits += 1
    return VerificationResponse(**json.loads(raw))


async def set(name: str, address: str, response: VerificationResponse) -> None:
    conn = await _get_connection()
    if conn is None:
        return

    key = _cache_key(name, address)
    try:
        await conn.set(key, response.model_dump_json(), ex=_ttl_seconds())
    except RedisError:
        return


async def stats() -> dict[str, int | float | bool]:
    total = _hits + _misses
    hit_rate = (_hits / total) if total else 0.0
    return {
        "hits": _hits,
        "misses": _misses,
        "hit_rate": hit_rate,
        "available": _available is not False,
    }


async def init() -> None:
    """Eagerly establish (and ping) the Redis connection pool."""
    await _get_connection()


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
