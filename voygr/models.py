from pydantic import BaseModel


class VerificationRequest(BaseModel):
    name: str
    address: str


class VerificationResponse(BaseModel):
    existence_status: str
    open_closed_status: str
    request_id: str | None = None
    validation_timestamp: str | None = None
    latency_ms: float = 0.0
    cache_hit: bool = False
