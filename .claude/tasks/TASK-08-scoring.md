# TASK-08 — Confidence scoring

## Objective
Map VOYGR API responses to a confidence percentage, a verdict enum, and an
enrichment flag — mirroring the confidence model visible in VOYGR's own product UI.

## Dependencies
TASK-02 complete.

## Context
VOYGR's product UI (voygr.tech) shows a "Confidence" percentage alongside an
"Evidence" panel for each place, with an "Enrich" CTA when confidence is low
(we saw 34% confidence on one example). This tells us their model treats
confidence as a spectrum, not a binary. GuardLayer should mirror this — not
just pass/fail, but a graduated confidence score with an enrichment suggestion.

## What to build

### Subtask 8.1 — scoring/confidence.py
Main function:
```python
def score(verification: VerificationResponse) -> tuple[float, Verdict, bool]:
    """
    Returns (confidence: float, verdict: Verdict, needs_enrichment: bool)
    """
```

Scoring logic:
```
existence_status = not_exists          → confidence 0.0,  FATAL_FLAW
existence_status = uncertain           → confidence 0.5,  UNCERTAIN
existence_status = exists AND
  open_closed_status = closed          → confidence 0.0,  FATAL_FLAW
existence_status = exists AND
  open_closed_status = uncertain       → confidence 0.6,  FLAGGED
existence_status = exists AND
  open_closed_status = open            → confidence 0.95, VERIFIED
```

`needs_enrichment`: True when confidence < CONFIDENCE_THRESHOLD (env var, default 0.70)
`fatal_flaw_reason`: populated only for FATAL_FLAW verdicts
  - "place does not exist" for not_exists
  - "place is permanently closed" for exists + closed

### Subtask 8.2 — Threshold configuration
Read `CONFIDENCE_THRESHOLD` from env via pydantic-settings.
Default: 0.70. Acceptable range: 0.0–1.0.
Raise a startup validation error if the value is outside this range.

### Subtask 8.3 — tests/test_scoring.py
Write tests BEFORE implementation.

Test cases (one per scoring path):
- `test_not_exists_is_fatal_flaw`: confidence=0.0, FATAL_FLAW, reason populated
- `test_exists_and_closed_is_fatal_flaw`: confidence=0.0, FATAL_FLAW
- `test_exists_and_open_is_verified`: confidence=0.95, VERIFIED
- `test_uncertain_existence_is_uncertain`: confidence=0.5, UNCERTAIN
- `test_exists_uncertain_open_is_flagged`: confidence=0.6, FLAGGED
- `test_needs_enrichment_below_threshold`: confidence=0.6 < 0.70 → True
- `test_no_enrichment_above_threshold`: confidence=0.95 > 0.70 → False
- `test_threshold_is_configurable`: patch CONFIDENCE_THRESHOLD to 0.90,
  confidence=0.95 still passes (> 0.90)

## Acceptance criteria
- [ ] All 5 scoring paths covered by tests
- [ ] `needs_enrichment` correctly reflects CONFIDENCE_THRESHOLD
- [ ] `fatal_flaw_reason` is populated for both FATAL_FLAW cases
- [ ] Threshold validation rejects values outside 0.0–1.0
- [ ] All scoring tests pass

## Verification commands
```bash
make test tests/test_scoring.py -v
python -c "
from voygr.models import VerificationResponse
from scoring.confidence import score
v = VerificationResponse(existence_status='exists', open_closed_status='closed')
confidence, verdict, needs_enrichment = score(v)
print(confidence, verdict, needs_enrichment)  # 0.0 FATAL_FLAW False
"
```

## Commit checkpoint
`git commit -m "TASK-08: confidence scoring with graduated verdicts"`

## Claude Code notes
- This is the simplest module in the project but the most important to get
  exactly right — every output the user sees flows through here
- Write all 8 tests before a single line of implementation
- The configurable threshold test is the one most likely to be forgotten —
  write it first
