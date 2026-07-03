# TASK-03 — Entity extraction module

## Objective
Build the module that parses arbitrary LLM free-text responses into structured
`{name, address}` entity pairs using Claude Haiku via the Anthropic API.

## Dependencies
TASK-01, TASK-02 complete.

## Reference — reuse from DevBench
The DevBench Category C pipeline already parses LLM responses into entity pairs
for the batch POI validation prompts. Before writing anything here, read:
`@../devbench/runner/extract.py`
`@../devbench/runner/models.py`
Reuse the extraction prompt pattern — do not reinvent it.

## What to build

### Subtask 3.1 — extraction/extractor.py
Implement `async def extract(text: str) -> ExtractionResult`.

System prompt must:
- Instruct the model to return ONLY valid JSON
- Define the exact schema: `{"entities": [{"name": "...", "address": "..."}]}`
- Instruct it to return `{"entities": []}` when no places are mentioned
- Handle address_inferred case: when only a venue name is present with no
  address, set `"address": "<venue name>"` and `"address_inferred": true`

Use `claude-haiku-3-5` — fast and cheap for this structured task.
Set `max_tokens=500` — entity lists are short, this is generous.

### Subtask 3.2 — Normalization helper
`extraction/normalizer.py`: `normalize(text: str) -> str`
Lowercase, strip extra whitespace, remove punctuation except commas and hyphens.
Used by the cache key generator — must be deterministic and idempotent.

### Subtask 3.3 — Error handling
- Anthropic API unavailable → return `ExtractionResult(entities=[], ...)`
  with a warning log, do not raise
- API returns malformed JSON → attempt to extract any JSON object from the
  response text before giving up (models sometimes add leading text despite
  the system prompt)
- Empty input text → return empty entities immediately, do not call the API

### Subtask 3.4 — tests/test_extraction.py
Write tests BEFORE implementing Subtask 3.1.

Required fixtures in `tests/fixtures/llm_responses.json`:
1. A Claude-style response recommending 3 SF restaurants (from DevBench Category C)
2. A response with only venue names, no addresses
3. A response mentioning a permanently closed restaurant by name
4. An empty/refusal response ("I can't help with that")
5. A response with zero place mentions (purely factual answer)

Test cases:
- `test_extracts_multiple_entities`: fixture 1 → 3 entities returned
- `test_infers_address_when_missing`: fixture 2 → address_inferred=True
- `test_handles_empty_response`: fixture 4 → empty entities list, no exception
- `test_handles_no_places`: fixture 5 → empty entities list, no exception
- `test_normalizer_is_idempotent`: normalize(normalize(x)) == normalize(x)

## Acceptance criteria
- [ ] `extract()` returns correct entity count for all 5 fixtures
- [ ] `address_inferred` is set correctly on venue-only responses
- [ ] API unavailability returns empty list, does not raise
- [ ] All extraction tests pass
- [ ] Normalizer is idempotent

## Verification commands
```bash
make test tests/test_extraction.py -v
python -c "
import asyncio
from extraction.extractor import extract
r = asyncio.run(extract('I love Tartine Bakery on Guerrero St in San Francisco'))
print(r.entities)
"
```

## Commit checkpoint
`git commit -m "TASK-03: entity extraction via Claude Haiku"`

## Claude Code notes
- Write tests/fixtures/llm_responses.json first, then test_extraction.py,
  then extractor.py — strict TDD order
- Use `think` before writing the system prompt — the prompt quality directly
  determines downstream pipeline quality
- Run the live sanity check command above before committing
