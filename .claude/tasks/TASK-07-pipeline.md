# TASK-07 — Verification pipeline orchestrator

## Objective
Build the main orchestrator that wires extraction → cache → verify → score →
persist into a single async function: `guard(text, source_llm) -> GuardedResponse`.

## Dependencies
TASK-03, TASK-04, TASK-05, TASK-06 all complete.

## What to build

### Subtask 7.1 — pipeline/guard.py
Main function: `async def guard(response: LLMResponse) -> GuardedResponse`

Exact flow per entity (run concurrently via asyncio.gather):
```
1. Extract entities from response.text (extraction/extractor.py)
2. For each entity concurrently:
   a. Check Redis cache (cache/redis_cache.py)
   b. Cache miss → call VOYGR API (voygr/client.py)
   c. Cache miss → write result to Redis
   d. Score the verification result (scoring/confidence.py)
   e. Write to PostgreSQL (storage/postgres.py) — non-blocking
3. Assemble GuardedResponse
4. Generate summary string
```

### Subtask 7.2 — Concurrent entity verification
Use `asyncio.gather(*[verify_entity(e) for e in entities], return_exceptions=True)`.
`return_exceptions=True` is mandatory — it means one entity raising an exception
does not cancel the others. Handle each result: if it's an Exception, log it
and produce an UNCERTAIN EntityVerdict for that entity.

### Subtask 7.3 — Summary string generation
`summary` field of GuardedResponse should be a single human-readable sentence:
- 0 fatal flaws: `"All {n} places verified — {flagged} flagged for enrichment."`
- 1+ fatal flaws: `"{n} fatal flaw(s) detected: {names}. {flagged} flagged for enrichment."`

### Subtask 7.4 — run_id
Generate a UUID4 `run_id` per guard() call. Attach it to GuardedResponse.
Useful for correlating a specific /guard call with its verification_log rows.

### Subtask 7.5 — tests/test_pipeline.py
This is the most important test file in the project.

Mock all four dependencies (extractor, voygr client, redis cache, postgres)
so the pipeline tests are pure unit tests with no external services needed.

Test cases:
- `test_full_pipeline_all_verified`: 3 entities, all VOYGR returns open/exists
- `test_pipeline_catches_fatal_flaw`: 1 of 3 entities is closed — that one is
  FATAL_FLAW, others are VERIFIED, run completes normally
- `test_pipeline_uses_cache_on_second_call`: same entity twice, VOYGR called once
- `test_pipeline_handles_extraction_failure`: extractor returns empty → empty
  GuardedResponse, no exception
- `test_pipeline_handles_one_entity_exception`: one entity's verify() raises —
  others still complete, that entity is UNCERTAIN
- `test_concurrent_verification`: verify that asyncio.gather is actually called
  (entities verified concurrently, not sequentially)
- `test_summary_string_correct_for_flaws`: fatal flaw → summary includes names
- `test_run_id_is_unique`: two calls → two different run_ids

## Acceptance criteria
- [ ] One entity exception does not abort the pipeline
- [ ] Entities are verified concurrently (not sequentially)
- [ ] Cache is checked before VOYGR API is called
- [ ] PostgreSQL write failure does not surface to caller
- [ ] Summary string matches both templates correctly
- [ ] All pipeline tests pass

## Verification commands
```bash
make test tests/test_pipeline.py -v
# End-to-end sanity with real services:
python -c "
import asyncio
from pipeline.guard import guard
from pipeline.models import LLMResponse
r = asyncio.run(guard(LLMResponse(text='I recommend Tartine Bakery on Guerrero St, SF')))
print(r.summary)
print(r.fatal_flaw_count, r.flagged_count)
"
```

## Commit checkpoint
`git commit -m "TASK-07: pipeline orchestrator with concurrent entity verification"`

## Claude Code notes
- Use `ultrathink` before writing this task — the concurrent error handling
  pattern with `return_exceptions=True` is subtle
- Ask Claude to explain the asyncio.gather error handling approach before
  writing any code
- The test for concurrent verification is non-trivial — ask Claude to think
  through how to assert that entities were NOT verified sequentially
