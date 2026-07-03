from fastapi import APIRouter

from cache import redis_cache
from storage import postgres
from voygr import client as voygr_client

router = APIRouter(tags=["observability"])


@router.get("/health")
async def health_endpoint() -> dict:
    cache_stats = await redis_cache.stats()
    postgres_ok = await postgres.is_available()
    return {
        "status": "ok",
        "service": "guardlayer",
        "dependencies": {
            "redis": "ok" if cache_stats["available"] else "unavailable",
            "postgres": "ok" if postgres_ok else "unavailable",
            "voygr_api": "configured" if voygr_client._api_key else "not_configured",
        },
    }
