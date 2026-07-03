from enum import Enum

from pydantic import BaseModel

from extraction.models import ExtractedEntity
from voygr.models import VerificationResponse


class Verdict(str, Enum):
    VERIFIED = "verified"
    FLAGGED = "flagged"
    FATAL_FLAW = "fatal_flaw"
    UNCERTAIN = "uncertain"


class EntityVerdict(BaseModel):
    entity: ExtractedEntity
    verification: VerificationResponse
    verdict: Verdict
    confidence: float
    needs_enrichment: bool
    fatal_flaw_reason: str | None = None
