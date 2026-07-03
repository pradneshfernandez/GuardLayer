import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.routes import guard, health, history, stats
from cache import redis_cache
from storage.migrate import run_migrations

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    await run_migrations()
    await redis_cache.init()
    yield
    await redis_cache.close()


def create_app() -> FastAPI:
    app = FastAPI(title="GuardLayer", lifespan=_lifespan)

    app.include_router(guard.router)
    app.include_router(stats.router)
    app.include_router(history.router)
    app.include_router(health.router)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception processing %s %s", request.method, request.url)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "An unexpected error occurred."},
        )

    return app


app = create_app()
