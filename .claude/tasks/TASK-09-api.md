# TASK-09 — FastAPI endpoints

## Objective
Wire the pipeline into a clean HTTP API with five endpoints. The API layer
contains zero business logic — it is plumbing only.

## Dependencies
TASK-07 and TASK-08 complete.

## What to build

### Subtask 9.1 — api/routes/guard.py

`POST /guard`
```
Request:  GuardRequest { text: str, source_llm: str | None }
Response: GuardedResponse
Tags:     ["verification"]
```

`POST /guard/batch`
```
Request:  BatchGuardRequest { responses: list[GuardRequest] (max 20) }
Response: list[GuardedResponse]
Tags:     ["verification"]
```
Process all items concurrently via `asyncio.gather`.
Reject requests with > 20 items: HTTP 422.

### Subtask 9.2 — api/routes/stats.py

`GET /stats`
```
Response: StatsResponse (from storage.get_stats() merged with cache.stats())
Tags:     ["observability"]
```

### Subtask 9.3 — api/routes/history.py

`GET /history`
```
Query params: limit: int = 20 (max 100), offset: int = 0
Response:     list[HistoryItem]
Tags:         ["observability"]
```

### Subtask 9.4 — api/routes/health.py
Update the existing health endpoint to include dependency status:
```json
{
  "status": "ok",
  "service": "guardlayer",
  "dependencies": {
    "redis": "ok" | "unavailable",
    "postgres": "ok" | "unavailable",
    "voygr_api": "configured" | "not_configured"
  }
}
```

### Subtask 9.5 — api/main.py
Register all route modules. Add startup/shutdown events:
- Startup: run database migrations, initialize Redis connection pool
- Shutdown: close Redis connection pool

Add global exception handler that returns:
```json
{"error": "internal_error", "message": "..."}
```
for any unhandled exception — never expose raw stack traces to the caller.

### Subtask 9.6 — tests/test_api.py
Use FastAPI's `TestClient` (synchronous) and `AsyncClient` (async) from `httpx`.
Mock the pipeline.guard function at the FastAPI dependency layer.

Test cases:
- `test_guard_returns_200_with_valid_text`
- `test_guard_batch_returns_200_for_multiple_responses`
- `test_guard_batch_rejects_21_items_with_422`
- `test_guard_returns_200_even_when_fatal_flaw_found`
- `test_health_returns_all_dependency_status`
- `test_stats_returns_correct_shape`
- `test_history_respects_limit_param`
- `test_unhandled_exception_returns_clean_error` (not a raw stack trace)

## Acceptance criteria
- [ ] `POST /guard` with real text returns GuardedResponse shape
- [ ] `POST /guard/batch` with 21 items returns 422
- [ ] Fatal flaw in response → HTTP 200 (not 4xx)
- [ ] `/health` includes dependency status for all three
- [ ] Raw stack traces never appear in API responses
- [ ] All API tests pass
- [ ] OpenAPI docs load at `/docs`

## Verification commands
```bash
make test tests/test_api.py -v
make run
curl -s -X POST http://localhost:8080/guard \
  -H "Content-Type: application/json" \
  -d '{"text":"I recommend Tartine Bakery on Guerrero St, San Francisco"}' \
  | python3 -m json.tool
curl -s http://localhost:8080/health | python3 -m json.tool
curl -s http://localhost:8080/docs   # should load in browser
```

## Commit checkpoint
`git commit -m "TASK-09: FastAPI endpoints — guard, batch, stats, history, health"`

## Claude Code notes
- Write tests/test_api.py before implementing any routes
- Keep every route handler under 10 lines — if it's longer, the logic is in
  the wrong place
- The global exception handler test (`test_unhandled_exception_returns_clean_error`)
  is the easiest to forget and the most important for production quality
