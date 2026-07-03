# GuardLayer

FastAPI middleware that intercepts LLM responses containing place recommendations,
extracts entity mentions, verifies each against VOYGR's business-status API, and
returns a guarded response with fatal flaws flagged before they reach the user.

Companion project to DevBench. Where DevBench measured the hallucination problem,
GuardLayer fixes it live. Demo case: all 7 LLM configs in VOYGR's Q1 report
confidently gave booking guidance to a permanently closed Buenos Aires restaurant.
GuardLayer catches that.

@docs/architecture.md

## Commands

```bash
make setup       # Start postgres, redis, app containers
make run         # Start the API on :8080
make test        # Run full test suite
make demo        # Run before/after demo against VOYGR's hardest published prompts
make down        # Stop containers, preserve volumes
make clean       # Stop containers, drop volumes
```

## Layout

```
extraction/      Entity extraction from LLM free text — uses Claude API
voygr/           VOYGR /v1/business-status client with retry and rate limiting
cache/           Redis caching layer for VOYGR API responses
storage/         PostgreSQL verification history and audit log
pipeline/        Main orchestrator — extract → cache → verify → score → persist
scoring/         Confidence scoring and enrichment flag logic
api/             FastAPI app, routes, request/response models
demo/            Before/after demo script using VOYGR's hardest published prompts
.claude/tasks/   Task definition files — one per implementation unit
tests/           Test suite; fixtures/ for offline canned responses
```

## Rules

**NEVER** make a VOYGR API call without checking Redis cache first.
Key format: `sha256(normalize(name) + "|" + normalize(address))`, TTL 7 days.

**NEVER** let a single entity failure abort the full pipeline. One entity fails —
log it, mark it uncertain, continue. The other entities still complete and write.

Every external call (VOYGR API, Redis, PostgreSQL) **MUST** degrade gracefully
when unavailable. Log a warning, return a sensible default, do not raise to the
caller. GuardLayer must be runnable with only the app container up.

All verification calls are **async**. Use `asyncio.gather` to verify entities
concurrently — do not verify sequentially.

All cross-module data **must** be Pydantic models. No raw dicts between modules.

The confidence threshold for `needs_enrichment: true` is **configurable via env**
(`CONFIDENCE_THRESHOLD`, default 70). Do not hardcode 70 anywhere in source.

## Environment

Copy `.env.example` → `.env`. Required vars:

```
ANTHROPIC_API_KEY          Used by extraction/ to parse LLM responses
VOYGR_API_KEY              Required for live verification — blank = uncertain verdict
VOYGR_API_BASE_URL         https://dev.voygr.tech
POSTGRES_HOST/PORT/DB/USER/PASSWORD
REDIS_URL                  redis://localhost:6379
CONFIDENCE_THRESHOLD       Default 70 — below this flags needs_enrichment: true
VOYGR_RATE_LIMIT_RPM       Default 10 — free tier limit
```

Full list with descriptions in `.env.example`.
