import asyncio
import logging
import uuid

from cache import redis_cache
from extraction.extractor import extract
from extraction.models import ExtractedEntity
from scoring.confidence import score
from scoring.models import EntityVerdict, Verdict
from storage import postgres
from voygr.client import verify
from voygr.models import VerificationResponse

from .models import GuardedResponse, LLMResponse

logger = logging.getLogger(__name__)


async def guard(response: LLMResponse) -> GuardedResponse:
    run_id = str(uuid.uuid4())
    extraction_result = await extract(response.text)

    results = await asyncio.gather(
        *[_verify_entity(entity, response.source_llm) for entity in extraction_result.entities],
        return_exceptions=True,
    )

    verdicts: list[EntityVerdict] = []
    for entity, result in zip(extraction_result.entities, results):
        if isinstance(result, BaseException):
            logger.warning("Entity verification failed for %s", entity.name, exc_info=result)
            verdicts.append(_uncertain_verdict(entity))
        else:
            verdicts.append(result)

    return _assemble_response(response.text, verdicts, run_id)


async def _verify_entity(entity: ExtractedEntity, source_llm: str | None) -> EntityVerdict:
    cached = await redis_cache.get(entity.name, entity.address)
    if cached is not None:
        verification = cached.model_copy(update={"cache_hit": True})
    else:
        verification = await verify(entity.name, entity.address)
        await redis_cache.set(entity.name, entity.address, verification)

    confidence, verdict, needs_enrichment, fatal_flaw_reason = score(verification)
    entity_verdict = EntityVerdict(
        entity=entity,
        verification=verification,
        verdict=verdict,
        confidence=confidence,
        needs_enrichment=needs_enrichment,
        fatal_flaw_reason=fatal_flaw_reason,
    )

    # storage failures are swallowed inside write_verification — never surfaced here
    await postgres.write_verification(entity_verdict, source_llm)

    return entity_verdict


def _uncertain_verdict(entity: ExtractedEntity) -> EntityVerdict:
    return EntityVerdict(
        entity=entity,
        verification=VerificationResponse(
            existence_status="uncertain", open_closed_status="uncertain"
        ),
        verdict=Verdict.UNCERTAIN,
        confidence=0.5,
        needs_enrichment=True,
    )


def _assemble_response(
    original_text: str, verdicts: list[EntityVerdict], run_id: str
) -> GuardedResponse:
    fatal_flaw_count = sum(1 for v in verdicts if v.verdict == Verdict.FATAL_FLAW)
    flagged_count = sum(1 for v in verdicts if v.verdict == Verdict.FLAGGED)
    verified_count = sum(1 for v in verdicts if v.verdict == Verdict.VERIFIED)
    uncertain_count = sum(1 for v in verdicts if v.verdict == Verdict.UNCERTAIN)

    return GuardedResponse(
        original_text=original_text,
        entities=verdicts,
        total_entities=len(verdicts),
        fatal_flaw_count=fatal_flaw_count,
        flagged_count=flagged_count,
        verified_count=verified_count,
        uncertain_count=uncertain_count,
        summary=_build_summary(verdicts, fatal_flaw_count, flagged_count),
        run_id=run_id,
    )


def _build_summary(verdicts: list[EntityVerdict], fatal_flaw_count: int, flagged_count: int) -> str:
    n = len(verdicts)
    if fatal_flaw_count == 0:
        return f"All {n} places verified — {flagged_count} flagged for enrichment."
    names = ", ".join(v.entity.name for v in verdicts if v.verdict == Verdict.FATAL_FLAW)
    return f"{fatal_flaw_count} fatal flaw(s) detected: {names}. {flagged_count} flagged for enrichment."
