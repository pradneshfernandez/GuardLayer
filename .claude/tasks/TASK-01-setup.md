# TASK-01 — Project setup and scaffolding

## Objective
Create the complete project skeleton: dependencies, containers, Makefile, and
a single working health endpoint that proves the stack is alive.

## Dependencies
None — this is the foundation all other tasks build on.

## What to build

### Subtask 1.1 — pyproject.toml
Define all dependencies. Required packages:
- `fastapi`, `uvicorn[standard]`
- `anthropic` (entity extraction)
- `httpx` (async HTTP for VOYGR client)
- `redis[hiredis]` (caching)
- `asyncpg`, `sqlalchemy[asyncio]` (postgres)
- `pydantic-settings` (env var loading)
- `tenacity` (retry logic)
- `rich` (demo output formatting)
- Dev: `pytest`, `pytest-asyncio`, `httpx` (test client), `pytest-cov`

### Subtask 1.2 — docker-compose.yml
Three services:
- `postgres`: `postgis/postgis:16-3.4`, port 5432, healthcheck on `pg_isready`
- `redis`: `redis:7-alpine`, port 6379, healthcheck on `redis-cli ping`
- `guardlayer`: built from local Dockerfile, port 8080, depends_on both above

### Subtask 1.3 — Dockerfile
- Base: `python:3.13-slim`
- Install dependencies from pyproject.toml
- CMD: `uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload`

### Subtask 1.4 — Makefile
```
make setup     → docker compose up -d --build, then run migrations
make run       → docker compose up guardlayer
make test      → pytest tests/ -v --cov
make demo      → python demo/run_demo.py
make logs      → docker compose logs -f
make down      → docker compose down
make clean     → docker compose down -v
```

### Subtask 1.5 — .env.example
Document every environment variable with a one-line comment. All vars listed
in CLAUDE.md must be present. Include sensible defaults where safe.

### Subtask 1.6 — Minimal FastAPI app
`api/main.py`: app factory with only `GET /health` implemented.
`GET /health` returns `{"status": "ok", "service": "guardlayer"}`.
All other routes come in TASK-09 — do not add them here.

### Subtask 1.7 — .gitignore
Include: `.env`, `.venv`, `__pycache__`, `*.pyc`, `.pytest_cache`,
`spatial/fixtures/*.pbf`, `.DS_Store`

## Acceptance criteria
- [ ] `docker compose up -d` starts all three containers with healthy status
- [ ] `curl http://localhost:8080/health` returns `{"status":"ok","service":"guardlayer"}`
- [ ] `make test` runs (0 tests pass, 0 fail — empty suite is fine at this stage)
- [ ] `.env` is in `.gitignore` and NOT committed

## Verification commands
```bash
docker compose ps                              # all three containers healthy
curl -s http://localhost:8080/health           # {"status":"ok","service":"guardlayer"}
curl -s http://localhost:8080/docs             # OpenAPI UI loads
git status                                     # .env should NOT appear
make test                                      # exits 0
```

## Commit checkpoint
`git commit -m "TASK-01: project setup, docker-compose, health endpoint"`

## Claude Code notes
- Ask Claude to show you the docker compose ps output before marking done
- If port 5432 conflicts with a local postgres, change the host port to 5433
  in docker-compose.yml (container port stays 5432)
