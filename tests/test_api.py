from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from extraction.models import ExtractedEntity
from pipeline.models import GuardedResponse
from scoring.models import EntityVerdict, Verdict
from voygr.models import VerificationResponse


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _guarded_response(fatal_flaw_count: int = 0, verdict: Verdict = Verdict.VERIFIED) -> GuardedResponse:
    entity_verdict = EntityVerdict(
        entity=ExtractedEntity(name="Cafe Velvet", address="123 Main St"),
        verification=VerificationResponse(existence_status="exists", open_closed_status="open"),
        verdict=verdict,
        confidence=0.95,
        needs_enrichment=False,
    )
    return GuardedResponse(
        original_text="I recommend Cafe Velvet",
        entities=[entity_verdict],
        total_entities=1,
        fatal_flaw_count=fatal_flaw_count,
        flagged_count=0,
        verified_count=1 if fatal_flaw_count == 0 else 0,
        uncertain_count=0,
        summary="All 1 places verified — 0 flagged for enrichment.",
        run_id="00000000-0000-0000-0000-000000000000",
    )


def test_guard_returns_200_with_valid_text(client):
    with patch("api.routes.guard.guard", new=AsyncMock(return_value=_guarded_response())):
        response = client.post("/guard", json={"text": "I recommend Cafe Velvet"})
    assert response.status_code == 200
    assert response.json()["total_entities"] == 1


def test_guard_batch_returns_200_for_multiple_responses(client):
    with patch("api.routes.guard.guard", new=AsyncMock(return_value=_guarded_response())):
        response = client.post(
            "/guard/batch", json={"responses": [{"text": "a"}, {"text": "b"}]}
        )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_guard_batch_rejects_21_items_with_422(client):
    response = client.post(
        "/guard/batch",
        json={"responses": [{"text": f"item {i}"} for i in range(21)]},
    )
    assert response.status_code == 422


def test_guard_returns_200_even_when_fatal_flaw_found(client):
    flawed = _guarded_response(fatal_flaw_count=1, verdict=Verdict.FATAL_FLAW)
    with patch("api.routes.guard.guard", new=AsyncMock(return_value=flawed)):
        response = client.post("/guard", json={"text": "Cafe Velvet is closed"})
    assert response.status_code == 200
    assert response.json()["fatal_flaw_count"] == 1


def test_health_returns_all_dependency_status(client):
    with (
        patch(
            "api.routes.health.redis_cache.stats",
            new=AsyncMock(return_value={"available": True, "hits": 0, "misses": 0, "hit_rate": 0.0}),
        ),
        patch("api.routes.health.postgres.is_available", new=AsyncMock(return_value=True)),
        patch("api.routes.health.voygr_client._api_key", "some-key"),
    ):
        response = client.get("/health")
    body = response.json()
    assert body["status"] == "ok"
    assert body["dependencies"] == {"redis": "ok", "postgres": "ok", "voygr_api": "configured"}


def test_stats_returns_correct_shape(client):
    with (
        patch(
            "api.routes.stats.postgres.get_stats",
            new=AsyncMock(
                return_value={
                    "total_verified": 10,
                    "fatal_flaw_count": 1,
                    "flagged_count": 2,
                    "avg_confidence": 0.8,
                }
            ),
        ),
        patch("api.routes.stats.redis_cache.stats", new=AsyncMock(return_value={"hit_rate": 0.5})),
    ):
        response = client.get("/stats")
    assert response.status_code == 200
    assert response.json() == {
        "total_verified": 10,
        "fatal_flaw_count": 1,
        "flagged_count": 2,
        "cache_hit_rate": 0.5,
        "avg_confidence": 0.8,
    }


def test_history_respects_limit_param(client):
    rows = [
        {
            "entity_name": "Cafe Velvet",
            "address": "123 Main St",
            "verdict": "verified",
            "confidence": 0.9,
            "verified_at": "2026-01-01T00:00:00Z",
        }
    ]
    get_history_mock = AsyncMock(return_value=rows)
    with patch("api.routes.history.postgres.get_history", new=get_history_mock):
        response = client.get("/history?limit=5&offset=0")
    assert response.status_code == 200
    get_history_mock.assert_awaited_once_with(limit=5, offset=0)


def test_unhandled_exception_returns_clean_error(client):
    with patch("api.routes.guard.guard", new=AsyncMock(side_effect=RuntimeError("boom"))):
        response = client.post("/guard", json={"text": "Cafe Velvet"})
    assert response.status_code == 500
    assert response.json() == {"error": "internal_error", "message": "An unexpected error occurred."}
    assert "Traceback" not in response.text
