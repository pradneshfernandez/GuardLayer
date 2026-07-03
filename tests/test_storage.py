import pytest

import storage.postgres as postgres_module
from extraction.models import ExtractedEntity
from scoring.models import EntityVerdict, Verdict
from storage.migrate import run_migrations
from voygr.models import VerificationResponse


@pytest.fixture(autouse=True)
async def _clean_table():
    postgres_module._pool = None
    postgres_module._unavailable = False

    await run_migrations()
    pool = await postgres_module._get_pool()
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE verification_log")

    yield

    await postgres_module.close()
    postgres_module._unavailable = False


def _make_verdict(verdict: Verdict, confidence: float) -> EntityVerdict:
    return EntityVerdict(
        entity=ExtractedEntity(name="Cafe Velvet", address="123 Main St"),
        verification=VerificationResponse(existence_status="exists", open_closed_status="open"),
        verdict=verdict,
        confidence=confidence,
        needs_enrichment=False,
    )


@pytest.mark.asyncio
async def test_write_and_read_back():
    await postgres_module.write_verification(_make_verdict(Verdict.VERIFIED, 0.9), source_llm="test-llm")
    history = await postgres_module.get_history(limit=10)
    assert len(history) == 1
    assert history[0]["entity_name"] == "Cafe Velvet"
    assert history[0]["verdict"] == "verified"


@pytest.mark.asyncio
async def test_stats_counts_correctly():
    await postgres_module.write_verification(_make_verdict(Verdict.FATAL_FLAW, 0.95), source_llm=None)
    await postgres_module.write_verification(_make_verdict(Verdict.FLAGGED, 0.6), source_llm=None)
    await postgres_module.write_verification(_make_verdict(Verdict.VERIFIED, 0.99), source_llm=None)

    stats = await postgres_module.get_stats()
    assert stats["total_verified"] == 3
    assert stats["fatal_flaw_count"] == 1
    assert stats["flagged_count"] == 1


@pytest.mark.asyncio
async def test_handles_postgres_unavailable(monkeypatch):
    monkeypatch.setattr(postgres_module, "_dsn", lambda: "postgresql://bad:bad@localhost:1/nope")
    postgres_module._pool = None
    postgres_module._unavailable = False

    result = await postgres_module.write_verification(
        _make_verdict(Verdict.VERIFIED, 0.9), source_llm=None
    )
    assert result is None
    assert await postgres_module.get_history() == []
    assert await postgres_module.get_stats() == {
        "total_verified": 0,
        "fatal_flaw_count": 0,
        "flagged_count": 0,
        "avg_confidence": 0.0,
    }


@pytest.mark.asyncio
async def test_migration_is_idempotent():
    await run_migrations()
    await run_migrations()
