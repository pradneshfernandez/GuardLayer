import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from extraction.extractor import extract
from extraction.normalizer import normalize

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "llm_responses.json").read_text())


class FakeTextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class FakeResponse:
    def __init__(self, content_text):
        self.content = [FakeTextBlock(content_text)]


def _mock_response(payload: dict) -> FakeResponse:
    return FakeResponse(json.dumps(payload))


@pytest.mark.asyncio
async def test_extracts_multiple_entities():
    payload = {
        "entities": [
            {"name": "Tartine Bakery", "address": "600 Guerrero St, San Francisco", "address_inferred": False},
            {"name": "State Bird Provisions", "address": "1529 Fillmore St, San Francisco", "address_inferred": False},
            {"name": "Zuni Cafe", "address": "1658 Market St, San Francisco", "address_inferred": False},
        ]
    }
    with patch(
        "extraction.extractor._client.messages.create",
        new=AsyncMock(return_value=_mock_response(payload)),
    ):
        result = await extract(FIXTURES["three_sf_restaurants"])
    assert len(result.entities) == 3


@pytest.mark.asyncio
async def test_infers_address_when_missing():
    payload = {
        "entities": [
            {"name": "Cafe Velvet", "address": "Cafe Velvet", "address_inferred": True},
            {"name": "The Blue Door", "address": "The Blue Door", "address_inferred": True},
            {"name": "Nightingale Lounge", "address": "Nightingale Lounge", "address_inferred": True},
        ]
    }
    with patch(
        "extraction.extractor._client.messages.create",
        new=AsyncMock(return_value=_mock_response(payload)),
    ):
        result = await extract(FIXTURES["venue_names_only"])
    assert len(result.entities) == 3
    assert all(e.address_inferred for e in result.entities)


@pytest.mark.asyncio
async def test_handles_empty_response():
    payload = {"entities": []}
    with patch(
        "extraction.extractor._client.messages.create",
        new=AsyncMock(return_value=_mock_response(payload)),
    ):
        result = await extract(FIXTURES["refusal"])
    assert result.entities == []


@pytest.mark.asyncio
async def test_handles_no_places():
    payload = {"entities": []}
    with patch(
        "extraction.extractor._client.messages.create",
        new=AsyncMock(return_value=_mock_response(payload)),
    ):
        result = await extract(FIXTURES["no_places"])
    assert result.entities == []


@pytest.mark.asyncio
async def test_empty_input_skips_api_call():
    with patch(
        "extraction.extractor._client.messages.create", new=AsyncMock()
    ) as mock_create:
        result = await extract("   ")
    mock_create.assert_not_called()
    assert result.entities == []


@pytest.mark.asyncio
async def test_api_unavailable_returns_empty_list():
    with patch(
        "extraction.extractor._client.messages.create",
        new=AsyncMock(side_effect=ConnectionError("unavailable")),
    ):
        result = await extract(FIXTURES["three_sf_restaurants"])
    assert result.entities == []


@pytest.mark.asyncio
async def test_handles_malformed_json_with_leading_text():
    payload = {"entities": [{"name": "Cafe Luna", "address": "Cafe Luna", "address_inferred": True}]}
    raw = "Sure, here you go:\n" + json.dumps(payload)
    with patch(
        "extraction.extractor._client.messages.create",
        new=AsyncMock(return_value=FakeResponse(raw)),
    ):
        result = await extract(FIXTURES["permanently_closed"])
    assert len(result.entities) == 1
    assert result.entities[0].name == "Cafe Luna"


def test_normalizer_is_idempotent():
    text = "  Cafe  Velvet,  123 Main-St!! "
    once = normalize(text)
    twice = normalize(once)
    assert once == twice
