# TASK-10 — Demo script and README

## Objective
Build the before/after demo that is the centrepiece of what VOYGR's founders
will see. This is the project's "product screenshot" — make it compelling.

## Dependencies
All previous tasks complete. VOYGR_API_KEY must be set for the demo to hit
the live API.

## What to build

### Subtask 10.1 — demo/hard_prompts.json
Hard-code the specific examples from VOYGR's own published report that exposed
the worst failures. These are not invented — they are documented in their Q1
2026 benchmarking report.

```json
[
  {
    "id": "buenos-aires-proper",
    "label": "Proper Restaurant, Buenos Aires (permanently closed)",
    "source": "VOYGR Q1 2026 Report, Section 4.3 — avg score 22.9/100 across all 7 configs",
    "text": "Can you help me book a dinner at Proper restaurant in Buenos Aires? I'm looking for a table for two on Saturday evening. What's the best way to make a reservation, and do they have any private dining options?",
    "source_llm": "simulation"
  },
  {
    "id": "medellin-cafe-velvet",
    "label": "Cafe Velvet, Medellín (permanently closed — hardest prompt in benchmark)",
    "source": "VOYGR Q1 2026 Report, Section 4.3 — avg score 34.6/100",
    "text": "What's the vibe at Cafe Velvet in Medellín? I'm visiting next week and want to know the best time to go, what to order, and whether I need a reservation.",
    "source_llm": "simulation"
  },
  {
    "id": "sf-discover-coffee",
    "label": "SF coffee discovery (baseline — should verify cleanly)",
    "source": "DevBench Category C baseline",
    "text": "I'm looking for specialty coffee shops in the Mission District that aren't chains. I care about single-origin beans and a good work environment. Any recommendations?",
    "source_llm": "simulation"
  }
]
```

### Subtask 10.2 — demo/run_demo.py
Use `rich` for terminal formatting. Output must be visually clear.

Structure:
```
GuardLayer Demo — VOYGR's hardest published prompts
════════════════════════════════════════════════════

[1/3] Proper Restaurant, Buenos Aires
Source: VOYGR Q1 2026 Report — avg score 22.9/100 across all 7 LLM configs

  LLM response (simulated):
  ┌─────────────────────────────────────────────────────┐
  │ Proper is one of Buenos Aires' finest...             │
  │ I'd recommend calling +54 11 XXXX for a reservation │
  └─────────────────────────────────────────────────────┘

  GuardLayer verdict:
  ┌──────────────┬────────────┬────────────────────────────────────┐
  │ Entity       │ Verdict    │ Detail                             │
  ├──────────────┼────────────┼────────────────────────────────────┤
  │ Proper       │ FATAL FLAW │ place is permanently closed        │
  └──────────────┴────────────┴────────────────────────────────────┘

  ✗ GuardLayer would have blocked this response from reaching the user.

────────────────────────────────────────────────────
Summary: 2/3 fatal flaws caught · 1/3 verified clean
```

### Subtask 10.3 — README.md
Sections:
1. What it is (2 sentences)
2. The problem it solves — use the Proper Buenos Aires finding directly:
   *"All 7 LLM configurations in VOYGR's Q1 2026 report confidently provided
   booking guidance to a permanently closed restaurant. GuardLayer catches this."*
3. How it works — 4-step numbered list (extract → check cache → verify → flag)
4. Quick start — `make setup && make run` then a curl example
5. Demo — `make demo` and a screenshot placeholder
6. API reference — table of the 5 endpoints with one-liner descriptions
7. Attribution — same block as DevBench (VOYGR report link, dev-tools link,
   non-affiliation disclaimer)
8. License — MIT

## Acceptance criteria
- [ ] `make demo` runs without error and prints a formatted table
- [ ] Demo correctly shows FATAL_FLAW for the Buenos Aires and Medellín prompts
- [ ] Demo shows VERIFIED or FLAGGED for the SF coffee prompt
- [ ] README is readable cold — someone who hasn't seen any other file
      understands what it is and how to run it within 60 seconds
- [ ] Attribution block includes both VOYGR repo links

## Verification commands
```bash
make demo           # must print the Rich-formatted table cleanly
make run            # API starts
curl -s -X POST http://localhost:8080/guard \
  -H "Content-Type: application/json" \
  -d '{"text":"Book me a table at Proper restaurant in Buenos Aires"}' \
  | python3 -m json.tool
# fatal_flaw_count should be > 0 if VOYGR_API_KEY is set
```

## Commit checkpoint
`git commit -m "TASK-10: demo script and README"`
`git tag v0.1.0`

## Claude Code notes
- Write demo/hard_prompts.json first before any code — the content is the
  most important design decision in this task
- Use `rich.table.Table` and `rich.panel.Panel` for formatting — they're
  already in the dependencies from TASK-01
- The README's second paragraph (the Buenos Aires finding) is the most
  important sentence in the project — review it carefully before committing
