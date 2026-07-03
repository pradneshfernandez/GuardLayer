# Error log

Issues hit during development, how they were diagnosed, and the fix. One
entry per issue, newest first.

---

## TASK-01 — `pytest` not found in container

**Symptom:** `docker compose exec guardlayer pytest tests/ -v --cov` failed
with `exec: "pytest": executable file not found in $PATH`.

**Cause:** Dockerfile ran `pip install .` (base deps only), so the `dev`
extras (`pytest`, `pytest-asyncio`, `pytest-cov`) were never installed in
the image.

**Fix:** Changed Dockerfile to `pip install ".[dev]"`.
