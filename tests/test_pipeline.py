import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

import pipeline.guard as guard_module
from extraction.models import ExtractedEntity, ExtractionResult
from pipeline.models import LLMResponse
from voygr.models import VerificationResponse


def _entity(name: str, address: str = "123 Main St") -> ExtractedEntity:
    return ExtractedEntity(name=name, address=address)


def _extraction_result(entities: list[ExtractedEntity]) -> ExtractionResult:
    return ExtractionResult(entities=entities, raw_text="text", extraction_latency_ms=1.0)


def _verification(existence: str = "exists", open_closed: str = "open") -> VerificationResponse:
    return VerificationResponse(existence_status=existence, open_closed_status=open_closed)


@pytest.fixture(autouse=True)
def _mock_dependencies(monkeypatch):
    monkeypatch.setattr(guard_module.redis_cache, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(guard_module.redis_cache, "set", AsyncMock(return_value=None))
    monkeypatch.setattr(guard_module.postgres, "write_verification", AsyncMock(return_value=None))


@pytest.mark.asyncio
async def test_full_pipeline_all_verified():
    entities = [_entity("A"), _entity("B"), _entity("C")]
    with (
        patch.object(guard_module, "extract", new=AsyncMock(return_value=_extraction_result(entities))),
        patch.object(guard_module, "verify", new=AsyncMock(return_value=_verification())),
    ):
        result = await guard_module.guard(LLMResponse(text="..."))

    assert result.total_entities == 3
    assert result.verified_count == 3
    assert result.fatal_flaw_count == 0


@pytest.mark.asyncio
async def test_pipeline_catches_fatal_flaw():
    entities = [_entity("A"), _entity("B"), _entity("Closed Place")]

    async def fake_verify(name, address):
        if name == "Closed Place":
            return _verification("exists", "closed")
        return _verification("exists", "open")

    with (
        patch.object(guard_module, "extract", new=AsyncMock(return_value=_extraction_result(entities))),
        patch.object(guard_module, "verify", new=AsyncMock(side_effect=fake_verify)),
    ):
        result = await guard_module.guard(LLMResponse(text="..."))

    assert result.fatal_flaw_count == 1
    assert result.verified_count == 2
    assert "Closed Place" in result.summary


@pytest.mark.asyncio
async def test_pipeline_uses_cache_on_second_call(monkeypatch):
    entities = [_entity("A")]
    verify_mock = AsyncMock(return_value=_verification())
    get_mock = AsyncMock(side_effect=[None, _verification()])
    set_mock = AsyncMock(return_value=None)

    monkeypatch.setattr(guard_module.redis_cache, "get", get_mock)
    monkeypatch.setattr(guard_module.redis_cache, "set", set_mock)

    with (
        patch.object(guard_module, "extract", new=AsyncMock(return_value=_extraction_result(entities))),
        patch.object(guard_module, "verify", new=verify_mock),
    ):
        await guard_module.guard(LLMResponse(text="..."))
        await guard_module.guard(LLMResponse(text="..."))

    assert verify_mock.call_count == 1
    assert get_mock.call_count == 2
    assert set_mock.call_count == 1


@pytest.mark.asyncio
async def test_pipeline_handles_extraction_failure():
    with patch.object(guard_module, "extract", new=AsyncMock(return_value=_extraction_result([]))):
        result = await guard_module.guard(LLMResponse(text="nothing to see here"))

    assert result.total_entities == 0
    assert result.entities == []


@pytest.mark.asyncio
async def test_pipeline_handles_one_entity_exception():
    entities = [_entity("A"), _entity("Boom"), _entity("C")]

    async def flaky_verify(name, address):
        if name == "Boom":
            raise RuntimeError("verification service exploded")
        return _verification()

    with (
        patch.object(guard_module, "extract", new=AsyncMock(return_value=_extraction_result(entities))),
        patch.object(guard_module, "verify", new=AsyncMock(side_effect=flaky_verify)),
    ):
        result = await guard_module.guard(LLMResponse(text="..."))

    assert result.total_entities == 3
    assert result.uncertain_count == 1
    assert result.verified_count == 2


@pytest.mark.asyncio
async def test_concurrent_verification():
    entities = [_entity("A"), _entity("B"), _entity("C")]

    async def slow_verify(name, address):
        await asyncio.sleep(0.2)
        return _verification()

    with (
        patch.object(guard_module, "extract", new=AsyncMock(return_value=_extraction_result(entities))),
        patch.object(guard_module, "verify", new=AsyncMock(side_effect=slow_verify)),
    ):
        start = time.monotonic()
        await guard_module.guard(LLMResponse(text="..."))
        elapsed = time.monotonic() - start

    # Sequential would take ~0.6s (3 * 0.2s); concurrent should be ~0.2s.
    assert elapsed < 0.4


@pytest.mark.asyncio
async def test_summary_string_correct_for_flaws():
    entities = [_entity("Cafe Luna")]
    with (
        patch.object(guard_module, "extract", new=AsyncMock(return_value=_extraction_result(entities))),
        patch.object(guard_module, "verify", new=AsyncMock(return_value=_verification("exists", "closed"))),
    ):
        result = await guard_module.guard(LLMResponse(text="..."))

    assert result.summary == "1 fatal flaw(s) detected: Cafe Luna. 0 flagged for enrichment."


@pytest.mark.asyncio
async def test_run_id_is_unique():
    with patch.object(guard_module, "extract", new=AsyncMock(return_value=_extraction_result([]))):
        r1 = await guard_module.guard(LLMResponse(text="a"))
        r2 = await guard_module.guard(LLMResponse(text="b"))

    assert r1.run_id != r2.run_id
