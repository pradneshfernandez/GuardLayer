# GuardLayer

FastAPI middleware that intercepts LLM responses containing place recommendations,
extracts entity mentions, verifies each against VOYGR's business-status API, and
returns a guarded response with fatal flaws flagged before they reach the user.

Companion project to DevBench. Where DevBench measured the hallucination problem,
GuardLayer fixes it live. Demo case: all 7 LLM configs in VOYGR's Q1 report
confidently gave booking guidance to a permanently closed Buenos Aires restaurant.
GuardLayer catches that.

## How it works

```
LLM response → extract entities → check cache → verify via VOYGR API
             → score confidence → persist → guarded response
```

See [docs/architecture.md](docs/architecture.md) for the full pipeline design and
[docs/structure.md](docs/structure.md) for the project layout.

## Getting started

```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY and VOYGR_API_KEY
make setup              # start postgres, redis, app containers
make run                # start the API on :8080
```

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

## License

MIT — see [LICENSE](LICENSE).
