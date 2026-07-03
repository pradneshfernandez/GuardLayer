from pydantic import BaseModel


class ExtractedEntity(BaseModel):
    name: str
    address: str
    address_inferred: bool = False


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    raw_text: str
    extraction_latency_ms: float
