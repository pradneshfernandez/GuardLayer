from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class GuardRequest(BaseModel):
    text: str
    source_llm: str | None = None


class BatchGuardRequest(BaseModel):
    responses: Annotated[list[GuardRequest], Field(max_length=20)]


class StatsResponse(BaseModel):
    total_verified: int
    fatal_flaw_count: int
    flagged_count: int
    cache_hit_rate: float
    avg_confidence: float


class HistoryItem(BaseModel):
    entity_name: str
    address: str
    verdict: str
    confidence: float
    verified_at: datetime
