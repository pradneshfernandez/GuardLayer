from fastapi import APIRouter

from api.models import StatsResponse
from cache import redis_cache
from storage import postgres

router = APIRouter(tags=["observability"])


@router.get("/stats", response_model=StatsResponse)
async def stats_endpoint() -> StatsResponse:
    db_stats = await postgres.get_stats()
    cache_stats = await redis_cache.stats()
    return StatsResponse(
        total_verified=db_stats["total_verified"],
        fatal_flaw_count=db_stats["fatal_flaw_count"],
        flagged_count=db_stats["flagged_count"],
        cache_hit_rate=cache_stats["hit_rate"],
        avg_confidence=db_stats["avg_confidence"],
    )
