# TASK-06 — PostgreSQL verification history

## Objective
Persist every verification outcome to PostgreSQL for audit, stats, and the
/history and /stats API endpoints.

## Dependencies
TASK-01, TASK-02 complete. (No dependency on TASK-03, 04, or 05.)

## What to build

### Subtask 6.1 — storage/migrations/001_init.sql
```sql
CREATE TABLE IF NOT EXISTS verification_log (
    id              SERIAL PRIMARY KEY,
    entity_name     TEXT NOT NULL,
    address         TEXT NOT NULL,
    existence_status TEXT NOT NULL,
    open_closed_status TEXT NOT NULL,
    verdict         TEXT NOT NULL,
    confidence      FLOAT NOT NULL,
    needs_enrichment BOOLEAN NOT NULL DEFAULT false,
    cache_hit       BOOLEAN NOT NULL DEFAULT false,
    source_llm      TEXT,
    verified_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_verification_log_verified_at
    ON verification_log (verified_at DESC);
CREATE INDEX IF NOT EXISTS idx_verification_log_verdict
    ON verification_log (verdict);
```

### Subtask 6.2 — storage/postgres.py
Three public functions:

```python
async def write_verification(verdict: EntityVerdict, source_llm: str | None) -> None
async def get_history(limit: int = 20, offset: int = 0) -> list[dict]
async def get_stats() -> dict
```

`get_stats()` returns:
```python
{
    "total_verified": int,
    "fatal_flaw_count": int,
    "flagged_count": int,
    "avg_confidence": float,
}
```

### Subtask 6.3 — Migration runner
`storage/migrate.py`: reads all `.sql` files from `storage/migrations/` in
filename order and executes them. Called by `make setup` on first run and
idempotent on subsequent runs (all migrations use `CREATE IF NOT EXISTS`).

### Subtask 6.4 — Graceful degradation
When PostgreSQL is unavailable:
- `write_verification()` logs a WARNING and returns None — does not raise
- `get_history()` returns empty list
- `get_stats()` returns all-zero dict
- The pipeline still returns a GuardedResponse — storage failure is not user-visible

### Subtask 6.5 — tests/test_storage.py
Use `pytest-asyncio` with a real test database (separate `devbench_test` db
in the docker-compose postgres, created in setup).

Test cases:
- `test_write_and_read_back`: write one verdict, get_history returns it
- `test_stats_counts_correctly`: write mix of verdicts, stats reflect counts
- `test_handles_postgres_unavailable`: mock unavailable connection, no exception
- `test_migration_is_idempotent`: run migration twice, no error

## Acceptance criteria
- [ ] Migration runs without error on fresh database
- [ ] Migration is idempotent (safe to run twice)
- [ ] write_verification + get_history round-trips correctly
- [ ] PostgreSQL unavailable → no exception, empty/zero returns
- [ ] All storage tests pass

## Verification commands
```bash
make test tests/test_storage.py -v
# Manual check:
docker exec devbench-postgres-1 psql -U devbench -d guardlayer -c \
  "SELECT COUNT(*) FROM verification_log;"
```

## Commit checkpoint
`git commit -m "TASK-06: PostgreSQL verification history with migration runner"`

## Claude Code notes
- Write the migration SQL first, then the tests, then the implementation
- Use `asyncpg` directly rather than SQLAlchemy ORM — the queries are
  simple enough that an ORM adds more complexity than it removes here
