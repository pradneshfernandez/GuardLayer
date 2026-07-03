from pydantic import BaseModel

from scoring.models import EntityVerdict


class LLMResponse(BaseModel):
    text: str
    source_llm: str | None = None


class GuardedResponse(BaseModel):
    original_text: str
    entities: list[EntityVerdict]
    total_entities: int
    fatal_flaw_count: int
    flagged_count: int
    verified_count: int
    uncertain_count: int
    summary: str
    run_id: str
