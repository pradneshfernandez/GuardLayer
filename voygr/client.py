import asyncio
import logging
import os
import time

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential, wait_random

from .models import VerificationResponse

logger = logging.getLogger(__name__)

_RETRY_STATUS_CODES = {429, 503, 504}


class _TokenBucket:
    def __init__(self, rate_per_minute: int):
        self._rate_per_minute = rate_per_minute
        self._tokens = float(rate_per_minute)
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._updated_at
                self._tokens = min(
                    float(self._rate_per_minute),
                    self._tokens + elapsed * (self._rate_per_minute / 60.0),
                )
                self._updated_at = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                wait_time = (1 - self._tokens) / (self._rate_per_minute / 60.0)
            await asyncio.sleep(wait_time)


def _rate_limit_rpm() -> int:
    return int(os.environ.get("VOYGR_RATE_LIMIT_RPM", "10"))


_bucket = _TokenBucket(_rate_limit_rpm())

_api_key = os.environ.get("VOYGR_API_KEY", "")
_api_base_url = os.environ.get("VOYGR_API_BASE_URL", "https://dev.voygr.tech")

if not _api_key:
    logger.warning("VOYGR_API_KEY not set — all verifications will return uncertain")
else:
    logger.debug("Using VOYGR_API_KEY ending in ...%s", _api_key[-4:])


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRY_STATUS_CODES
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException))


@retry(
    retry=retry_if_exception(_should_retry),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10) + wait_random(0, 1),
    reraise=True,
)
async def _post_verification(name: str, address: str) -> httpx.Response:
    await _bucket.acquire()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{_api_base_url}/v1/business-status",
            headers={
                "Authorization": f"Bearer {_api_key}",
                "Content-Type": "application/json",
            },
            json={"name": name, "address": address},
        )
    response.raise_for_status()
    return response


async def verify(name: str, address: str) -> VerificationResponse:
    if not _api_key:
        return VerificationResponse(
            existence_status="uncertain",
            open_closed_status="uncertain",
            latency_ms=0.0,
        )

    start = time.perf_counter()
    try:
        response = await _post_verification(name, address)
    except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException):
        logger.warning("VOYGR verification failed for %s", name, exc_info=True)
        return VerificationResponse(
            existence_status="uncertain",
            open_closed_status="uncertain",
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    data = response.json()
    latency_ms = (time.perf_counter() - start) * 1000
    return VerificationResponse(
        existence_status=data.get("existence_status", "uncertain"),
        open_closed_status=data.get("open_closed_status", "uncertain"),
        request_id=data.get("request_id"),
        validation_timestamp=data.get("validation_timestamp"),
        latency_ms=latency_ms,
        cache_hit=False,
    )
