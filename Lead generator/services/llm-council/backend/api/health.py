"""Health and readiness endpoints."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter

from ..config import get_settings
from ..schemas import HealthStatus

router = APIRouter(tags=["health"])


def _service_version() -> str:
    try:
        return version("llm-council")
    except PackageNotFoundError:
        return "0.0.0"


@router.get("/", response_model=HealthStatus)
@router.get("/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    settings = get_settings()
    return HealthStatus(
        status="ok" if settings.openrouter_api_key else "degraded",
        version=_service_version(),
        env=settings.env,
        council_models=settings.council_models,
        chairman_model=settings.chairman_model,
        openrouter_configured=bool(settings.openrouter_api_key),
    )


@router.get("/health/live")
async def liveness() -> dict:
    """Always returns 200 if the process is up — for Docker / k8s liveness."""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness() -> dict:
    """Returns 200 only when minimal runtime config is present."""
    settings = get_settings()
    ok = bool(settings.openrouter_api_key) and bool(settings.council_models)
    return {"status": "ready" if ok else "not_ready", "configured": ok}
