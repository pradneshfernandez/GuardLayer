---
paths:
  - "api/**/*.py"
---

# API layer rules

The API layer is HTTP plumbing only. No business logic lives here.
Every route handler must be ≤ 10 lines. If it's longer, the logic belongs
in pipeline/ or scoring/ instead.

POST /guard accepts { "text": str, "source_llm": str (optional) }
POST /guard/batch accepts { "responses": [{ "text": str }] }
GET /stats returns cache hit rate, total verified, fatal flaws caught, avg confidence
GET /history accepts ?limit=20&offset=0, returns paginated verification_log rows
GET /health returns { "status": "ok", "service": "guardlayer" }

Always return HTTP 200 even when entities have fatal flaws — a flaw is a valid
result, not an error. Reserve 4xx/5xx for actual request or service failures.

The /guard/batch endpoint must process items concurrently (asyncio.gather),
not sequentially. Cap batch size at 20 items — reject larger batches with 422.

Include OpenAPI tags on every route for clean auto-generated docs.
Do not disable the /docs endpoint — it's a feature, not a security risk here.
