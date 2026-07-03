# GuardLayer — Project Structure

```
guardlayer/
├── .claude/
│   ├── rules/
│   │   ├── extraction.md     ← path-scoped to extraction/** — system prompt rules, Haiku model, edge cases
│   │   ├── voygr_client.md   ← path-scoped to voygr/** — rate limiting, retry policy, key logging rules
│   │   └── api.md            ← path-scoped to api/** — route handler size limit, HTTP 200 for flaws
│   └── tasks/
│       ├── TASK-01-setup.md      ← docker-compose, Makefile, health endpoint
│       ├── TASK-02-models.md     ← all Pydantic models across all modules
│       ├── TASK-03-extraction.md ← entity extraction via Claude Haiku
│       ├── TASK-04-voygr-client.md ← VOYGR API client with retry and rate limiting
│       ├── TASK-05-cache.md      ← Redis caching with normalization
│       ├── TASK-06-storage.md    ← PostgreSQL verification history
│       ├── TASK-07-pipeline.md   ← main orchestrator (depends on 03–06)
│       ├── TASK-08-scoring.md    ← confidence scoring and verdict logic
│       ├── TASK-09-api.md        ← FastAPI endpoints
│       └── TASK-10-demo.md       ← demo script and README
├── docs/
│   ├── architecture.md       ← pipeline design, verdict enum, DB schema — imported by CLAUDE.md via @
│   ├── structure.md          ← this file
│   └── documentation.md      ← library-style reference docs (generated in TASK-10)
├── extraction/
│   ├── __init__.py
│   ├── extractor.py          ← async extract() → ExtractionResult via Claude Haiku
│   ├── normalizer.py         ← normalize(text) — shared with cache key generation
│   └── models.py             ← ExtractedEntity, ExtractionResult
├── voygr/
│   ├── __init__.py
│   ├── client.py             ← async verify() → VerificationResponse with retry + rate limit
│   └── models.py             ← VerificationRequest, VerificationResponse
├── cache/
│   ├── __init__.py
│   └── redis_cache.py        ← get(), set(), stats() — in-memory fallback when Redis down
├── storage/
│   ├── __init__.py
│   ├── postgres.py           ← write_verification(), get_history(), get_stats()
│   ├── migrate.py            ← migration runner — called by make setup
│   └── migrations/
│       └── 001_init.sql      ← verification_log table + indexes
├── pipeline/
│   ├── __init__.py
│   ├── guard.py              ← guard(LLMResponse) → GuardedResponse — main orchestrator
│   └── models.py             ← LLMResponse, GuardedResponse
├── scoring/
│   ├── __init__.py
│   ├── confidence.py         ← score(VerificationResponse) → (float, Verdict, bool)
│   └── models.py             ← Verdict enum, EntityVerdict
├── api/
│   ├── __init__.py
│   ├── main.py               ← FastAPI app factory, startup/shutdown events, global error handler
│   ├── models.py             ← GuardRequest, BatchGuardRequest, StatsResponse, HistoryItem
│   └── routes/
│       ├── guard.py          ← POST /guard, POST /guard/batch
│       ├── stats.py          ← GET /stats
│       ├── history.py        ← GET /history
│       └── health.py         ← GET /health (with dependency status)
├── demo/
│   ├── hard_prompts.json     ← VOYGR's hardest published prompts (Proper BA, Cafe Velvet)
│   └── run_demo.py           ← before/after demo with Rich-formatted terminal output
├── tests/
│   ├── __init__.py
│   ├── test_extraction.py    ← extraction module unit tests
│   ├── test_voygr_client.py  ← client unit tests using respx/MockTransport
│   ├── test_cache.py         ← cache tests using fakeredis
│   ├── test_pipeline.py      ← pipeline tests with all 4 dependencies mocked
│   ├── test_scoring.py       ← scoring unit tests (no external deps)
│   ├── test_api.py           ← FastAPI endpoint tests using httpx TestClient
│   └── fixtures/
│       ├── llm_responses.json    ← 5 canned LLM responses for extraction tests
│       └── voygr_responses.json  ← 5 canned VOYGR API responses for client tests
├── CLAUDE.md                 ← Claude Code instructions (70 lines) — imports @docs/architecture.md
├── CLAUDE.local.md           ← personal prefs — gitignored
├── README.md                 ← user-facing setup and context
├── Dockerfile                ← python:3.13-slim, installs deps, runs uvicorn
├── docker-compose.yml        ← postgres, redis, guardlayer app
├── Makefile                  ← setup / run / test / demo / down / clean
├── pyproject.toml            ← dependencies and project config
├── requirements.txt          ← generated from pyproject.toml
└── .env.example              ← all required env vars with descriptions
```

---

## File responsibilities

### .claude/rules/ — path-scoped Claude Code instructions

| File | Scoped to | Purpose |
|---|---|---|
| `extraction.md` | `extraction/**` | System prompt rules, Haiku model requirement, 3 edge cases |
| `voygr_client.md` | `voygr/**` | Token bucket rate limiting, retry policy, key logging rules |
| `api.md` | `api/**` | 10-line handler limit, HTTP 200 for flaws, batch size cap |

### extraction/

| File | Purpose |
|---|---|
| `extractor.py` | Calls Claude Haiku API, forces JSON output, handles 3 edge cases |
| `normalizer.py` | `normalize(text)` — lowercases and strips for consistent cache keys |
| `models.py` | `ExtractedEntity` (name, address, address_inferred), `ExtractionResult` |

### voygr/

| File | Purpose |
|---|---|
| `client.py` | Async HTTP client — token bucket rate limit, tenacity retry, graceful degradation |
| `models.py` | `VerificationRequest`, `VerificationResponse` |

### cache/

| File | Purpose |
|---|---|
| `redis_cache.py` | `get()`, `set()`, `stats()` — no-op fallback when Redis unavailable |

### storage/

| File | Purpose |
|---|---|
| `postgres.py` | `write_verification()`, `get_history()`, `get_stats()` |
| `migrate.py` | Runs SQL files from migrations/ in filename order — idempotent |
| `migrations/001_init.sql` | `verification_log` table and two indexes |

### pipeline/

| File | Purpose |
|---|---|
| `guard.py` | Main orchestrator — wires all 4 modules, concurrent entity verification |
| `models.py` | `LLMResponse`, `GuardedResponse` |

### scoring/

| File | Purpose |
|---|---|
| `confidence.py` | Maps VerificationResponse → (confidence float, Verdict, needs_enrichment bool) |
| `models.py` | `Verdict` enum, `EntityVerdict` |

### api/

| File | Purpose |
|---|---|
| `main.py` | App factory, startup/shutdown events, global exception handler |
| `models.py` | `GuardRequest`, `BatchGuardRequest`, `StatsResponse`, `HistoryItem` |
| `routes/guard.py` | `POST /guard`, `POST /guard/batch` |
| `routes/stats.py` | `GET /stats` |
| `routes/history.py` | `GET /history` |
| `routes/health.py` | `GET /health` with dependency status |

### demo/

| File | Purpose |
|---|---|
| `hard_prompts.json` | VOYGR's published worst-scoring prompts from Q1 2026 report |
| `run_demo.py` | Rich-formatted terminal before/after comparison |

### tests/

| File | Purpose |
|---|---|
| `test_extraction.py` | 5 fixture-based tests — no Anthropic API calls |
| `test_voygr_client.py` | Mock HTTP tests — no real VOYGR API calls |
| `test_cache.py` | fakeredis tests — no real Redis needed |
| `test_pipeline.py` | All 4 deps mocked — pure unit tests |
| `test_scoring.py` | Pure unit tests — no external deps at all |
| `test_api.py` | httpx TestClient — no real services needed |

---

## Build sequence

```
TASK-01 (setup)
    └── TASK-02 (models)
            ├── TASK-03 (extraction) ─┐
            ├── TASK-04 (voygr)      ├── TASK-07 (pipeline)
            ├── TASK-05 (cache)      ├──     └── TASK-09 (api)
            └── TASK-06 (storage)   ─┘              └── TASK-10 (demo)
                    └── TASK-08 (scoring) ──────────────────┘
```

Tasks 03–06 and 08 have no inter-dependencies — they can be built in parallel.

---

## Memory file load behaviour

| When | What loads |
|---|---|
| Every session | `CLAUDE.md` (70 lines) + `@docs/architecture.md` (80 lines) = ~150 lines total |
| Opening `extraction/**` | `.claude/rules/extraction.md` added to context |
| Opening `voygr/**` | `.claude/rules/voygr_client.md` added to context |
| Opening `api/**` | `.claude/rules/api.md` added to context |
| Personal prefs | `CLAUDE.local.md` (gitignored, machine-local only) |
