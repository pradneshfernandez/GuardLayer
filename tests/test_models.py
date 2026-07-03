from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from api.models import (
    BatchGuardRequest,
    GuardRequest,
    HistoryItem,
    StatsResponse,
)
from extraction.models import ExtractedEntity, ExtractionResult
from pipeline.models import GuardedResponse, LLMResponse
from scoring.models import EntityVerdict, Verdict
from voygr.models import VerificationRequest, VerificationResponse


def test_extracted_entity_defaults():
    entity = ExtractedEntity(name="Cafe Velvet", address="123 Main St")
    assert entity.address_inferred is False


def test_extracted_entity_requires_name_and_address():
    with pytest.raises(ValidationError):
        ExtractedEntity(name="Cafe Velvet")


def test_extraction_result():
    result = ExtractionResult(
        entities=[ExtractedEntity(name="Cafe Velvet", address="123 Main St")],
        raw_text="Visit Cafe Velvet at 123 Main St.",
        extraction_latency_ms=42.0,
    )
    assert len(result.entities) == 1


def test_verification_request_response():
    VerificationRequest(name="Cafe Velvet", address="123 Main St")
    response = VerificationResponse(existence_status="exists", open_closed_status="open")
    assert response.cache_hit is False
    assert response.latency_ms == 0.0


def test_verdict_enum_has_exactly_four_values():
    assert {v.value for v in Verdict} == {
        "verified",
        "flagged",
        "fatal_flaw",
        "uncertain",
    }


def test_entity_verdict():
    verdict = EntityVerdict(
        entity=ExtractedEntity(name="Cafe Velvet", address="123 Main St"),
        verification=VerificationResponse(
            existence_status="exists", open_closed_status="closed"
        ),
        verdict=Verdict.FATAL_FLAW,
        confidence=0.95,
        needs_enrichment=False,
        fatal_flaw_reason="Business is permanently closed",
    )
    assert verdict.verdict == Verdict.FATAL_FLAW


def test_entity_verdict_rejects_invalid_verdict():
    with pytest.raises(ValidationError):
        EntityVerdict(
            entity=ExtractedEntity(name="Cafe Velvet", address="123 Main St"),
            verification=VerificationResponse(
                existence_status="exists", open_closed_status="open"
            ),
            verdict="not_a_real_verdict",
            confidence=0.5,
            needs_enrichment=False,
        )


def test_llm_response_and_guarded_response():
    LLMResponse(text="Try Cafe Velvet.")
    guarded = GuardedResponse(
        original_text="Try Cafe Velvet.",
        entities=[],
        total_entities=0,
        fatal_flaw_count=0,
        flagged_count=0,
        verified_count=0,
        uncertain_count=0,
        summary="No entities found.",
        run_id="00000000-0000-0000-0000-000000000000",
    )
    assert guarded.total_entities == 0


def test_guard_request():
    GuardRequest(text="Try Cafe Velvet.")


def test_batch_guard_request_accepts_20_items():
    batch = BatchGuardRequest(responses=[GuardRequest(text="x") for _ in range(20)])
    assert len(batch.responses) == 20


def test_batch_guard_request_rejects_21_items():
    with pytest.raises(ValidationError):
        BatchGuardRequest(responses=[GuardRequest(text="x") for _ in range(21)])


def test_stats_response():
    StatsResponse(
        total_verified=10,
        fatal_flaw_count=1,
        flagged_count=2,
        cache_hit_rate=0.5,
        avg_confidence=0.8,
    )


def test_history_item():
    HistoryItem(
        entity_name="Cafe Velvet",
        address="123 Main St",
        verdict="fatal_flaw",
        confidence=0.95,
        verified_at=datetime.now(timezone.utc),
    )
