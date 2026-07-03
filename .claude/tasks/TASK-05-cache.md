# TASK-05 — Redis caching layer

## Objective
Cache VOYGR API responses in Redis so that the same place is never verified
twice within the TTL window — protecting the free-tier rate limit.

## Dependencies
TASK-01, TASK-02 complete. (No dependency on TASK-03 or TASK-04.)

## What to build

### Subtask 5.1 — cache/redis_cache.py
Three public functions:

```python
async def get(name: str, address: str) -> VerificationResponse | None
async def set(name: str, address: str, response: VerificationResponse) -> None
async def stats() -> dict[str, int | float]  # hits, misses, hit_rate
```

Cache key: `f"guardlayer:verify:{sha256(normalize(name) + '|' + normalize(address))[:16]}"`
Use the normalizer from `extraction/normalizer.py` — do not duplicate it.
TTL: read from `CACHE_TTL_SECONDS` env var, default 604800 (7 days).

### Subtask 5.2 — In-memory fallback
When Redis is unavailable (connection refused, timeout):
- Log `WARNING: Redis unavailable — falling back to no-op cache` once at startup
- `get()` always returns None (cache miss)
- `set()` is a no-op
- `stats()` returns `{"hits": 0, "misses": 0, "hit_rate": 0.0, "available": False}`
- The pipeline continues normally — a cache miss just means a VOYGR API call

### Subtask 5.3 — Connection management
Use a module-level Redis connection pool, not a new connection per call.
Initialize lazily on first use. Expose an `async def close()` function
called on FastAPI shutdown event.

### Subtask 5.4 — tests/test_cache.py
Write tests BEFORE implementation using `fakeredis[aioredis]` as the test double.

Test cases:
- `test_cache_miss_returns_none`
- `test_cache_set_then_get_returns_response`
- `test_cache_key_is_normalized` — same place with different casing hits same key
- `test_cache_respects_ttl` — mock time passing, check expiry
- `test_stats_tracks_hits_and_misses`
- `test_degrades_gracefully_when_redis_unavailable`

## Acceptance criteria
- [ ] Cache key is identical for "tartine bakery" and "Tartine Bakery"
- [ ] TTL is read from env var, not hardcoded
- [ ] Redis unavailable → no exception, pipeline continues
- [ ] Stats correctly count hits and misses across calls
- [ ] All cache tests pass

## Verification commands
```bash
make test tests/test_cache.py -v
# With Redis running:
python -c "
import asyncio
from cache.redis_cache import get, set, stats
from voygr.models import VerificationResponse
async def run():
    r = VerificationResponse(existence_status='exists', open_closed_status='open')
    await set('Ferry Building', 'SF', r)
    hit = await get('ferry building', 'sf')   # different casing
    print('Cache hit:', hit is not None)
    print(await stats())
asyncio.run(run())
"
```

## Commit checkpoint
`git commit -m "TASK-05: Redis caching with normalization and graceful fallback"`

## Claude Code notes
- Install `fakeredis[aioredis]` as a dev dependency for tests — it's the
  standard test double for async Redis and avoids needing a real Redis in CI
- The normalization test (same place different casing → same cache key) is the
  most important test here — write it first
