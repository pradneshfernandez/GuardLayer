import json
import time
from pathlib import Path

import httpx
import pytest
import respx

import voygr.client as client_module
from voygr.client import _TokenBucket, verify

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "voygr_responses.json").read_text())

BASE_URL = "https://test.voygr.example"


@pytest.fixture(autouse=True)
def _configure_client(monkeypatch):
    monkeypatch.setattr(client_module, "_api_key", "test-key")
    monkeypatch.setattr(client_module, "_api_base_url", BASE_URL)
    monkeypatch.setattr(client_module, "_bucket", _TokenBucket(rate_per_minute=1000))


@pytest.mark.asyncio
@respx.mock
async def test_returns_open_for_active_business():
    respx.post(f"{BASE_URL}/v1/business-status").mock(
        return_value=httpx.Response(200, json=FIXTURES["open_business"])
    )
    result = await verify("Tartine Bakery", "600 Guerrero St")
    assert result.existence_status == "exists"
    assert result.open_closed_status == "open"


@pytest.mark.asyncio
@respx.mock
async def test_returns_fatal_flaw_for_closed_business():
    respx.post(f"{BASE_URL}/v1/business-status").mock(
        return_value=httpx.Response(200, json=FIXTURES["closed_business"])
    )
    result = await verify("Cafe Luna", "123 Main St")
    assert result.existence_status == "exists"
    assert result.open_closed_status == "closed"


@pytest.mark.asyncio
@respx.mock
async def test_retries_on_429_and_succeeds():
    route = respx.post(f"{BASE_URL}/v1/business-status")
    route.side_effect = [
        httpx.Response(429, json=FIXTURES["rate_limited"]),
        httpx.Response(200, json=FIXTURES["open_business"]),
    ]
    result = await verify("Tartine Bakery", "600 Guerrero St")
    assert result.existence_status == "exists"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_does_not_retry_on_401():
    route = respx.post(f"{BASE_URL}/v1/business-status").mock(
        return_value=httpx.Response(401, json=FIXTURES["unauthorized"])
    )
    result = await verify("Tartine Bakery", "600 Guerrero St")
    assert result.existence_status == "uncertain"
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_returns_uncertain_when_no_api_key(monkeypatch):
    monkeypatch.setattr(client_module, "_api_key", "")
    result = await verify("Tartine Bakery", "600 Guerrero St")
    assert result.existence_status == "uncertain"
    assert result.open_closed_status == "uncertain"


@pytest.mark.asyncio
async def test_rate_limiter_respects_rpm_limit():
    bucket = _TokenBucket(rate_per_minute=60)  # 1 token/sec
    bucket._tokens = 0
    bucket._updated_at = time.monotonic()
    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.9
