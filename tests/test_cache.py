import asyncio

import fakeredis
import pytest

import cache.redis_cache as cache_module
from voygr.models import VerificationResponse


@pytest.fixture(autouse=True)
def _reset_cache_state(monkeypatch):
    monkeypatch.setattr(cache_module, "_pool", None)
    monkeypatch.setattr(cache_module, "_available", None)
    monkeypatch.setattr(cache_module, "_hits", 0)
    monkeypatch.setattr(cache_module, "_misses", 0)
    monkeypatch.setattr(cache_module, "_warned", False)


@pytest.fixture
def fake_redis(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(
        cache_module.redis_asyncio.Redis, "from_url", staticmethod(lambda *a, **kw: fake)
    )
    return fake


def _response() -> VerificationResponse:
    return VerificationResponse(existence_status="exists", open_closed_status="open")


@pytest.mark.asyncio
async def test_cache_miss_returns_none(fake_redis):
    result = await cache_module.get("Tartine Bakery", "600 Guerrero St")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_then_get_returns_response(fake_redis):
    await cache_module.set("Tartine Bakery", "600 Guerrero St", _response())
    result = await cache_module.get("Tartine Bakery", "600 Guerrero St")
    assert result is not None
    assert result.existence_status == "exists"
    assert result.open_closed_status == "open"


@pytest.mark.asyncio
async def test_cache_key_is_normalized(fake_redis):
    await cache_module.set("Tartine Bakery", "600 Guerrero St", _response())
    result = await cache_module.get("tartine bakery", "600 GUERRERO ST")
    assert result is not None


@pytest.mark.asyncio
async def test_cache_respects_ttl(fake_redis, monkeypatch):
    monkeypatch.setenv("CACHE_TTL_SECONDS", "1")
    await cache_module.set("Tartine Bakery", "600 Guerrero St", _response())
    await asyncio.sleep(1.2)
    result = await cache_module.get("Tartine Bakery", "600 Guerrero St")
    assert result is None


@pytest.mark.asyncio
async def test_stats_tracks_hits_and_misses(fake_redis):
    await cache_module.get("Tartine Bakery", "600 Guerrero St")  # miss
    await cache_module.set("Tartine Bakery", "600 Guerrero St", _response())
    await cache_module.get("Tartine Bakery", "600 Guerrero St")  # hit
    result = await cache_module.stats()
    assert result["hits"] == 1
    assert result["misses"] == 1
    assert result["hit_rate"] == 0.5
    assert result["available"] is True


@pytest.mark.asyncio
async def test_degrades_gracefully_when_redis_unavailable(monkeypatch):
    class _BrokenRedis:
        async def ping(self):
            raise ConnectionError("no redis here")

    monkeypatch.setattr(
        cache_module.redis_asyncio.Redis,
        "from_url",
        staticmethod(lambda *a, **kw: _BrokenRedis()),
    )

    result = await cache_module.get("Tartine Bakery", "600 Guerrero St")
    assert result is None

    await cache_module.set("Tartine Bakery", "600 Guerrero St", _response())  # no-op, no raise

    stats = await cache_module.stats()
    assert stats == {"hits": 0, "misses": 0, "hit_rate": 0.0, "available": False}
