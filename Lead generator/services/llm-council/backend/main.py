"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .api import conversations as conversations_api
from .api import council as council_api
from .api import health as health_api
from .config import get_settings
from .db.database import dispose_engine, init_db
from .dependencies import limiter
from .errors import register_error_handlers
from .logging import configure_logging, get_logger


def _rate_limit_handler(request, exc):  # noqa: ARG001
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "rate_limited",
                "message": "Too many requests. Slow down.",
                "details": {"detail": str(exc.detail) if hasattr(exc, "detail") else ""},
            }
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    configure_logging()
    log = get_logger("startup")
    settings = get_settings()

    if not settings.openrouter_api_key:
        log.warning(
            "openrouter_api_key_missing",
            hint="Copy .env.example to .env.local and add your OpenRouter key.",
        )

    await init_db()
    log.info(
        "service_ready",
        env=settings.env,
        host=settings.host,
        port=settings.port,
        council_models=settings.council_models,
        chairman_model=settings.chairman_model,
    )
    try:
        yield
    finally:
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="LLM Council API",
        description=(
            "Multi-LLM orchestration service for the Lead generator monorepo. "
            "Provides council-graded query/qualification/outreach/scrape-review."
        ),
        version="0.2.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    # Error handlers
    register_error_handlers(app)

    # Routers
    app.include_router(health_api.router)
    app.include_router(conversations_api.router)
    app.include_router(council_api.router)

    return app


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
