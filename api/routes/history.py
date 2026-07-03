from fastapi import APIRouter, Query

from api.models import HistoryItem
from storage import postgres

router = APIRouter(tags=["observability"])


@router.get("/history", response_model=list[HistoryItem])
async def history_endpoint(limit: int = Query(default=20, le=100), offset: int = 0) -> list[HistoryItem]:
    rows = await postgres.get_history(limit=limit, offset=offset)
    return [HistoryItem(**row) for row in rows]
