import json
import logging
import os
import re
import time

from anthropic import AsyncAnthropic

from .models import ExtractedEntity, ExtractionResult

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5"

_SYSTEM_PROMPT = """You extract place recommendations from LLM responses.

Return ONLY valid JSON matching this schema, with no other text:
{"entities": [{"name": "...", "address": "...", "address_inferred": false}]}

Rules:
- Extract every specific, named business or venue the text recommends or mentions.
- If the text mentions no places, return {"entities": []}.
- If a venue is named but no address is given, set "address" to the venue name
  itself and set "address_inferred" to true.
- If an address is given, set "address_inferred" to false.
"""

_client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY") or "unset")


async def extract(text: str) -> ExtractionResult:
    start = time.perf_counter()

    if not text.strip():
        return ExtractionResult(entities=[], raw_text=text, extraction_latency_ms=0.0)

    try:
        response = await _client.messages.create(
            model=_MODEL,
            max_tokens=500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )
    except Exception:
        logger.warning("Anthropic API unavailable during extraction", exc_info=True)
        return ExtractionResult(
            entities=[],
            raw_text=text,
            extraction_latency_ms=(time.perf_counter() - start) * 1000,
        )

    raw = "".join(block.text for block in response.content if block.type == "text")
    entities = _parse_entities(raw)
    return ExtractionResult(
        entities=entities,
        raw_text=text,
        extraction_latency_ms=(time.perf_counter() - start) * 1000,
    )


def _parse_entities(raw: str) -> list[ExtractedEntity]:
    data = _load_json_object(raw)
    if data is None:
        logger.warning("Could not extract JSON from extraction response: %r", raw)
        return []

    entities = []
    for item in data.get("entities", []):
        name = item.get("name")
        if not name:
            continue
        address = item.get("address") or name
        address_inferred = item.get("address_inferred", not item.get("address"))
        entities.append(
            ExtractedEntity(name=name, address=address, address_inferred=address_inferred)
        )
    return entities


def _load_json_object(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
