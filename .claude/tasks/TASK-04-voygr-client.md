# TASK-04 — VOYGR API client

## Objective
Build a production-grade async HTTP client for VOYGR's /v1/business-status
endpoint with rate limiting, retry logic, and graceful degradation.

## Dependencies
TASK-01, TASK-02 complete.

## Reference — reuse from DevBench
The DevBench Category C verification already calls this exact endpoint.
Before writing anything, read:
`@../devbench/runner/verify.py`
`@../devbench/runner/providers/anthropic.py` (retry pattern to reuse)
Extract the retry and backoff logic — do not rewrite it from scratch.

## What to build

### Subtask 4.1 — voygr/client.py
Implement `async def verify(name: str, address: str) -> VerificationResponse`.

Endpoint: `POST {VOYGR_API_BASE_URL}/v1/business-status`
Headers: `Authorization: Bearer {VOYGR_API_KEY}`, `Content-Type: application/json`
Body: `{"name": name, "address": address}`

### Subtask 4.2 — Rate limiting
Implement an async token bucket at `VOYGR_RATE_LIMIT_RPM` (default 10).
Use `asyncio.Semaphore` or a token bucket implementation — not `asyncio.sleep`
at the call site. The bucket must be shared across all concurrent callers via
a module-level singleton, not created per-call.

### Subtask 4.3 — Retry logic
Use `tenacity`:
- `stop_after_attempt(3)`
- `wait_exponential(multiplier=1, min=2, max=10)` + `wait_random(0, 1)` for jitter
- Retry on: 429, 503, 504, `httpx.ConnectError`, `httpx.TimeoutException`
- Do NOT retry on: 401, 400, 422

### Subtask 4.4 — Graceful degradation
When `VOYGR_API_KEY` is blank or absent:
- Log `WARNING: VOYGR_API_KEY not set — all verifications will return uncertain`
  exactly ONCE at module import time, not on every call
- Every call returns `VerificationResponse(existence_status="uncertain",
  open_closed_status="uncertain", latency_ms=0.0)`

### Subtask 4.5 — tests/test_voygr_client.py
Write tests BEFORE implementing the client.

Use `httpx.MockTransport` or `respx` to mock HTTP calls.
Required fixtures in `tests/fixtures/voygr_responses.json`:
1. Valid open business response
2. Valid closed business response  
3. Not-exists response
4. 429 rate limit response
5. 401 unauthorized response

Test cases:
- `test_returns_open_for_active_business`
- `test_returns_fatal_flaw_for_closed_business`
- `test_retries_on_429_and_succeeds`
- `test_does_not_retry_on_401`
- `test_returns_uncertain_when_no_api_key`
- `test_rate_limiter_respects_rpm_limit`

## Acceptance criteria
- [ ] Client makes correct HTTP call to VOYGR endpoint
- [ ] Retries on 429/503/504, not on 401/400
- [ ] Returns `uncertain` (not exception) when key is absent
- [ ] Rate limiter prevents > VOYGR_RATE_LIMIT_RPM calls per minute
- [ ] All client tests pass

## Verification commands
```bash
make test tests/test_voygr_client.py -v
# With a real key set in .env:
python -c "
import asyncio
from voygr.client import verify
r = asyncio.run(verify('Ferry Building', '1 Ferry Building, San Francisco, CA 94111'))
print(r)
"
```

## Commit checkpoint
`git commit -m "TASK-04: VOYGR API client with rate limiting and retry"`

## Claude Code notes
- Use `think hard` before writing the token bucket — async rate limiting is
  subtle and easy to get wrong under concurrent load
- Write the mock transport fixtures first, then the tests, then the client
- The rate limiter test is the trickiest — ask Claude to explain its approach
  before implementing it
