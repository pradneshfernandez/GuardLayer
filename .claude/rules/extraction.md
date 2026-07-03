---
paths:
  - "extraction/**/*.py"
---

# Extraction module rules

The extraction module's only job is parsing LLM text into {name, address} pairs.
It must not call VOYGR, touch Redis, or know anything about verification.

Always use a system prompt that forces strict JSON output. Include explicit
instructions to return an empty array rather than hallucinating entities when
no places are mentioned. Example system prompt shape:

```
You extract place mentions from text. Return ONLY valid JSON: {"entities": [{"name": "...", "address": "..."}]}.
If no places are mentioned return {"entities": []}.
No preamble, no explanation, no markdown fences.
```

Handle three edge cases explicitly — do not ignore them:
1. Venue name with no address mentioned → use the venue name as address too,
   flag `address_inferred: true` on the entity
2. Multiple venues in one response → return all of them, not just the first
3. LLM response is itself an error or refusal → return empty entities list,
   do not raise

Use `anthropic` SDK, not raw HTTP. Use `claude-haiku-3-5` for extraction —
it's fast and cheap for this structured task; do not use Sonnet here.
