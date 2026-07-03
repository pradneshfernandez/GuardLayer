# TASK-02 — Core Pydantic models

## Objective
Define every Pydantic model that crosses a module boundary. All other tasks
import from here — getting these right first prevents refactoring later.

## Dependencies
TASK-01 complete.

## What to build

### Subtask 2.1 — extraction/models.py
```python
class ExtractedEntity(BaseModel):
    name: str
    address: str
    address_inferred: bool = False   # True when address was not explicit in text

class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    raw_text: str                    # Original LLM response text
    extraction_latency_ms: float
```

### Subtask 2.2 — voygr/models.py
```python
class VerificationRequest(BaseModel):
    name: str
    address: str

class VerificationResponse(BaseModel):
    existence_status: str            # exists / not_exists / uncertain
    open_closed_status: str          # open / closed / uncertain
    request_id: str | None = None
    validation_timestamp: str | None = None
    latency_ms: float = 0.0
    cache_hit: bool = False
```

### Subtask 2.3 — scoring/models.py
```python
class Verdict(str, Enum):
    VERIFIED = "verified"
    FLAGGED = "flagged"
    FATAL_FLAW = "fatal_flaw"
    UNCERTAIN = "uncertain"

class EntityVerdict(BaseModel):
    entity: ExtractedEntity
    verification: VerificationResponse
    verdict: Verdict
    confidence: float                # 0.0–1.0
    needs_enrichment: bool
    fatal_flaw_reason: str | None = None
```

### Subtask 2.4 — pipeline/models.py
```python
class LLMResponse(BaseModel):
    text: str
    source_llm: str | None = None

class GuardedResponse(BaseModel):
    original_text: str
    entities: list[EntityVerdict]
    total_entities: int
    fatal_flaw_count: int
    flagged_count: int
    verified_count: int
    uncertain_count: int
    summary: str                     # human-readable one-liner
    run_id: str                      # UUID for this guard call
```

### Subtask 2.5 — api/models.py
```python
class GuardRequest(BaseModel):
    text: str
    source_llm: str | None = None

class BatchGuardRequest(BaseModel):
    responses: list[GuardRequest]
    model_config = ConfigDict(json_schema_extra={"maxItems": 20})

class StatsResponse(BaseModel):
    total_verified: int
    fatal_flaw_count: int
    flagged_count: int
    cache_hit_rate: float
    avg_confidence: float

class HistoryItem(BaseModel):
    entity_name: str
    address: str
    verdict: str
    confidence: float
    verified_at: datetime
```

### Subtask 2.6 — Tests
`tests/test_models.py`: validate every model with valid and invalid inputs.
Check: required fields, optional defaults, enum validation for Verdict,
`maxItems` constraint on BatchGuardRequest (reject > 20 items).

## Acceptance criteria
- [ ] All models importable from their respective modules
- [ ] `Verdict` enum covers exactly four values: VERIFIED, FLAGGED, FATAL_FLAW, UNCERTAIN
- [ ] `BatchGuardRequest` rejects a list of 21 items
- [ ] All model tests pass

## Verification commands
```bash
python -c "from extraction.models import ExtractedEntity, ExtractionResult; print('OK')"
python -c "from scoring.models import Verdict; print(list(Verdict))"
make test
```

## Commit checkpoint
`git commit -m "TASK-02: core Pydantic models across all modules"`

## Claude Code notes
- Use `think` before writing these — the Verdict enum and GuardedResponse summary
  field are the two design decisions most likely to need iteration later
- Write Subtask 2.6 (tests) BEFORE writing the models, not after
