import asyncio

from fastapi import APIRouter

from api.models import BatchGuardRequest, GuardRequest
from pipeline.guard import guard
from pipeline.models import GuardedResponse, LLMResponse

router = APIRouter(tags=["verification"])


@router.post("/guard", response_model=GuardedResponse)
async def guard_endpoint(request: GuardRequest) -> GuardedResponse:
    return await guard(LLMResponse(text=request.text, source_llm=request.source_llm))


@router.post("/guard/batch", response_model=list[GuardedResponse])
async def guard_batch_endpoint(request: BatchGuardRequest) -> list[GuardedResponse]:
    llm_responses = [LLMResponse(text=r.text, source_llm=r.source_llm) for r in request.responses]
    return list(await asyncio.gather(*[guard(r) for r in llm_responses]))
