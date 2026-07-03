import logging
import os

import asyncpg

from scoring.models import EntityVerdict

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_unavailable = False


def _dsn() -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "guardlayer")
    user = os.environ.get("POSTGRES_USER", "guardlayer")
    password = os.environ.get("POSTGRES_PASSWORD", "guardlayer")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


async def _get_pool() -> asyncpg.Pool | None:
    global _pool, _unavailable
    if _unavailable:
        return None
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(_dsn(), min_size=1, max_size=5)
        except (OSError, asyncpg.PostgresError):
            logger.warning(
                "PostgreSQL unavailable — verification history disabled", exc_info=True
            )
            _unavailable = True
            return None
    return _pool


async def write_verification(verdict: EntityVerdict, source_llm: str | None) -> None:
    pool = await _get_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO verification_log
                    (entity_name, address, existence_status, open_closed_status,
                     verdict, confidence, needs_enrichment, cache_hit, source_llm)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                verdict.entity.name,
                verdict.entity.address,
                verdict.verification.existence_status,
                verdict.verification.open_closed_status,
                verdict.verdict.value,
                verdict.confidence,
                verdict.needs_enrichment,
                verdict.verification.cache_hit,
                source_llm,
            )
    except asyncpg.PostgresError:
        logger.warning("Failed to write verification log entry", exc_info=True)


async def get_history(limit: int = 20, offset: int = 0) -> list[dict]:
    pool = await _get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT entity_name, address, verdict, confidence, verified_at
                FROM verification_log
                ORDER BY verified_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
    except asyncpg.PostgresError:
        logger.warning("Failed to read verification history", exc_info=True)
        return []
    return [dict(row) for row in rows]


async def get_stats() -> dict:
    zero_stats = {
        "total_verified": 0,
        "fatal_flaw_count": 0,
        "flagged_count": 0,
        "avg_confidence": 0.0,
    }
    pool = await _get_pool()
    if pool is None:
        return zero_stats
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) AS total_verified,
                    COUNT(*) FILTER (WHERE verdict = 'fatal_flaw') AS fatal_flaw_count,
                    COUNT(*) FILTER (WHERE verdict = 'flagged') AS flagged_count,
                    COALESCE(AVG(confidence), 0.0) AS avg_confidence
                FROM verification_log
                """
            )
    except asyncpg.PostgresError:
        logger.warning("Failed to compute verification stats", exc_info=True)
        return zero_stats
    return {
        "total_verified": row["total_verified"],
        "fatal_flaw_count": row["fatal_flaw_count"],
        "flagged_count": row["flagged_count"],
        "avg_confidence": float(row["avg_confidence"]),
    }


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
