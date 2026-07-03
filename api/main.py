from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="GuardLayer")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "guardlayer"}

    return app


app = create_app()
