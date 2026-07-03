---
paths:
  - "voygr/**/*.py"
---

# VOYGR client rules

The VOYGR client's only job is making HTTP calls to /v1/business-status and
returning a typed response. It must not score, cache, or persist anything.

Rate limiting: implement a token bucket at VOYGR_RATE_LIMIT_RPM (default 10).
Do not use a simple sleep — use an async token bucket so concurrent callers
share the same budget without blocking each other unnecessarily.

Retry policy: exponential backoff with jitter, max 3 retries.
Retry on: 429, 503, 504, and connection errors.
Do NOT retry on: 401 (bad key), 400 (bad request), 422 (validation error).

When VOYGR_API_KEY is absent or blank:
- Log a single WARNING at startup, not on every call
- Return VerificationResponse(existence_status="uncertain",
  open_closed_status="uncertain") for every call
- Do not raise, do not return None

Never log the API key value, even partially. Log only the last 4 characters
at DEBUG level to confirm which key is in use.

The free tier endpoint is https://dev.voygr.tech — do not hardcode this,
read it from VOYGR_API_BASE_URL env var.
