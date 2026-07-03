from pydantic import Field
from pydantic_settings import BaseSettings

from voygr.models import VerificationResponse

from .models import Verdict

_NOT_EXISTS_REASON = "place does not exist"
_CLOSED_REASON = "place is permanently closed"


class ScoringSettings(BaseSettings):
    confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)


def _threshold() -> float:
    return ScoringSettings().confidence_threshold


def score(verification: VerificationResponse) -> tuple[float, Verdict, bool, str | None]:
    """Map a VerificationResponse to (confidence, verdict, needs_enrichment, fatal_flaw_reason)."""
    if verification.existence_status == "not_exists":
        confidence, verdict, reason = 0.0, Verdict.FATAL_FLAW, _NOT_EXISTS_REASON
    elif verification.existence_status == "exists" and verification.open_closed_status == "closed":
        confidence, verdict, reason = 0.0, Verdict.FATAL_FLAW, _CLOSED_REASON
    elif verification.existence_status == "exists" and verification.open_closed_status == "uncertain":
        confidence, verdict, reason = 0.6, Verdict.FLAGGED, None
    elif verification.existence_status == "exists" and verification.open_closed_status == "open":
        confidence, verdict, reason = 0.95, Verdict.VERIFIED, None
    else:
        confidence, verdict, reason = 0.5, Verdict.UNCERTAIN, None

    needs_enrichment = confidence < _threshold()
    return confidence, verdict, needs_enrichment, reason
