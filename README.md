# GuardLayer

GuardLayer is a FastAPI middleware that sits between an LLM and its user. It
extracts place recommendations from LLM free text, verifies each one against
a business-status API, and returns a guarded response with fatal flaws
flagged before they ever reach the user.

## The problem it solves

All 7 LLM configurations in VOYGR's Q1 2026 report confidently provided
booking guidance to a permanently closed restaurant. GuardLayer catches this.

LLMs recommend places by pattern-matching on training data, with no live
knowledge of whether a business still exists or is still open. GuardLayer
adds that missing verification step as middleware, so a hallucinated or
stale recommendation gets flagged — or blocked — instead of reaching the
user as confident, wrong advice.

## How it works

1. **Extract** — parse the LLM's free text into structured `{name, address}`
   entity mentions (via Claude Haiku).
2. **Check cache** — look up each entity in Redis; skip verification on a
   hit.
3. **Verify** — on a cache miss, call the business-status API and cache the
   result.
4. **Flag** — score each result into a confidence value and a verdict
   (`verified` / `flagged` / `fatal_flaw` / `uncertain`), and assemble a
   guarded response with a human-readable summary.

See [docs/architecture.md](docs/architecture.md) for the full pipeline design
and [docs/structure.md](docs/structure.md) for the project layout.

## Quick start

```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY and VOYGR_API_KEY
make setup              # start postgres, redis, app containers
make run                # start the API on :8080
```

```bash
curl -s -X POST http://localhost:8080/guard \
  -H "Content-Type: application/json" \
  -d '{"text":"I recommend Tartine Bakery on Guerrero St, San Francisco"}' \
  | python3 -m json.tool
```

## Demo

```bash
make demo
```

Runs the pipeline against the exact hardest-scoring prompts from VOYGR's own
Q1 2026 report (a permanently-closed restaurant in Buenos Aires, a
permanently-closed cafe in Medellín — the hardest prompt in their benchmark
— and a clean baseline SF coffee-shop query), and prints a before/after
verdict table for each.

> **Status: this repo does not currently have live `ANTHROPIC_API_KEY` /
> `VOYGR_API_KEY` credentials configured.** `make demo` runs end-to-end and
> degrades gracefully (0 entities extracted, "verified clean" by default —
> see [`.claude/handoff.md`](.claude/handoff.md) for the exact behavior),
> but it cannot show real `FATAL_FLAW` verdicts for the Buenos Aires and
> Medellín prompts until both keys are set in `.env`. The pipeline, scoring,
> and API code paths are fully implemented and unit-tested (62 tests, 98%
> coverage) independent of live credentials — what's left is plugging in
> real keys and re-running the demo to capture the actual before/after
> screenshot.

## API reference

| Endpoint           | Method | Description                                          |
| ------------------- | ------ | ----------------------------------------------------- |
| `/guard`            | POST   | Verify all place mentions in one LLM response          |
| `/guard/batch`      | POST   | Same, for up to 20 responses concurrently               |
| `/stats`            | GET    | Cache hit rate, total verified, fatal flaws, avg confidence |
| `/history`          | GET    | Paginated verification log (`?limit=20&offset=0`)      |
| `/health`           | GET    | Service status plus Redis/Postgres/VOYGR dependency status |

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
docs/            Architecture and project structure documentation
```

## Environment

Copy `.env.example` to `.env`. Required vars:

```
ANTHROPIC_API_KEY          Used by extraction/ to parse LLM responses
VOYGR_API_KEY              Required for live verification — blank = uncertain verdict
VOYGR_API_BASE_URL         https://dev.voygr.tech
POSTGRES_HOST/PORT/DB/USER/PASSWORD
REDIS_URL                  redis://localhost:6379
CONFIDENCE_THRESHOLD       Default 0.70 (0.0-1.0) — below this flags needs_enrichment: true
VOYGR_RATE_LIMIT_RPM       Default 10 — free tier limit
```

Full list with descriptions in `.env.example`.

## Development process

Built iteratively with Claude Code — see `.claude/tasks/` for the task
breakdown used to build each module and `.claude/rules/` for the
path-scoped constraints enforced during development.

## Testing

```bash
make test
```

All tests run offline against fixtures/mocks — no live Anthropic, VOYGR, Redis,
or Postgres connections required.

## What's yet to be done

- **Live credentials** — `ANTHROPIC_API_KEY` and `VOYGR_API_KEY` are not
  configured in this environment. Every code path that depends on them
  (extraction, verification) is implemented, tested, and degrades
  gracefully without them, but the actual live before/after demo output
  (real `FATAL_FLAW` verdicts on the Buenos Aires / Medellín prompts) has
  not been captured yet.
- A demo screenshot/recording captured against the live APIs, to replace
  the placeholder description above.

## Attribution

This project integrates with [VOYGR](https://voygr.tech)'s
[Business Validation API](https://github.com/voygr-tech/dev-tools)
to verify LLM-recommended places. The permanently-closed venue examples used
in the demo are drawn from VOYGR's
[Q1 2026 LLM Local Search Benchmark](https://github.com/voygr-tech/llm-local-search-benchmark-report)
(Section 4.3).

This is an independent, unofficial project and is not affiliated with or
endorsed by VOYGR.

Companion project: DevBench, which measured this hallucination problem;
GuardLayer is the live mitigation.

## Limitations

- **VOYGR rate limiting is per-process, not distributed.** The token
  bucket in `voygr/client.py` is a module-level singleton — it enforces
  `VOYGR_RATE_LIMIT_RPM` correctly for one running instance, but running
  multiple GuardLayer replicas gives each one its own independent budget
  instead of a shared one.
- **No rate limiting on the extraction path.** `voygr/client.py` throttles
  calls to VOYGR; `extraction/extractor.py` has no equivalent limiter on
  calls to the Anthropic API. A large `/guard/batch` request can fan out an
  unbounded burst of concurrent Anthropic calls.
- **The Postgres write is on the request's critical path.** `pipeline/guard.py`
  awaits `storage.postgres.write_verification()` directly rather than firing
  it in the background. A failed write is swallowed (per the graceful-
  degradation design), but a *slow* — not down — Postgres adds real latency
  to every `/guard` call.
- **No authentication on GuardLayer's own API.** `/guard`, `/guard/batch`,
  `/stats`, and `/history` have no API key, token, or auth dependency —
  anyone with network access to the service can call them.
- **`/history` uses offset-based pagination**, which is simple but doesn't
  scale past a large `verification_log` table (each page still scans past
  the offset).
- **Never exercised against a live, successful VOYGR or Anthropic response**
  in this environment — see "What's yet to be done" above. The test suite
  covers both APIs thoroughly via fixtures and mocks, and the graceful-
  degradation paths are verified against real 401s, but a genuine
  `FATAL_FLAW` verdict from a live VOYGR call has not been observed.
- **Confidence scoring is five fixed buckets**, not a continuous score —
  it maps directly off VOYGR's `existence_status`/`open_closed_status`
  pair. It can't distinguish, for example, "temporarily closed for
  renovation" from "permanently closed," because VOYGR's own response
  schema doesn't currently expose that distinction either.

## License

MIT — see [LICENSE](LICENSE).
