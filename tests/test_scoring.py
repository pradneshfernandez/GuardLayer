import pytest

from scoring.confidence import score
from scoring.models import Verdict
from voygr.models import VerificationResponse


def test_not_exists_is_fatal_flaw():
    v = VerificationResponse(existence_status="not_exists", open_closed_status="uncertain")
    confidence, verdict, needs_enrichment, reason = score(v)
    assert confidence == 0.0
    assert verdict == Verdict.FATAL_FLAW
    assert reason == "place does not exist"


def test_exists_and_closed_is_fatal_flaw():
    v = VerificationResponse(existence_status="exists", open_closed_status="closed")
    confidence, verdict, needs_enrichment, reason = score(v)
    assert confidence == 0.0
    assert verdict == Verdict.FATAL_FLAW
    assert reason == "place is permanently closed"


def test_exists_and_open_is_verified():
    v = VerificationResponse(existence_status="exists", open_closed_status="open")
    confidence, verdict, needs_enrichment, reason = score(v)
    assert confidence == 0.95
    assert verdict == Verdict.VERIFIED
    assert reason is None


def test_uncertain_existence_is_uncertain():
    v = VerificationResponse(existence_status="uncertain", open_closed_status="uncertain")
    confidence, verdict, needs_enrichment, reason = score(v)
    assert confidence == 0.5
    assert verdict == Verdict.UNCERTAIN


def test_exists_uncertain_open_is_flagged():
    v = VerificationResponse(existence_status="exists", open_closed_status="uncertain")
    confidence, verdict, needs_enrichment, reason = score(v)
    assert confidence == 0.6
    assert verdict == Verdict.FLAGGED
    assert reason is None


def test_needs_enrichment_below_threshold():
    v = VerificationResponse(existence_status="exists", open_closed_status="uncertain")
    _, _, needs_enrichment, _ = score(v)
    assert needs_enrichment is True  # 0.6 < 0.70 default threshold


def test_no_enrichment_above_threshold():
    v = VerificationResponse(existence_status="exists", open_closed_status="open")
    _, _, needs_enrichment, _ = score(v)
    assert needs_enrichment is False  # 0.95 > 0.70 default threshold


def test_threshold_is_configurable(monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.90")
    v = VerificationResponse(existence_status="exists", open_closed_status="open")
    _, _, needs_enrichment, _ = score(v)
    assert needs_enrichment is False  # 0.95 still passes at a 0.90 threshold


def test_threshold_rejects_out_of_range(monkeypatch):
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "1.5")
    v = VerificationResponse(existence_status="exists", open_closed_status="open")
    with pytest.raises(Exception):
        score(v)
