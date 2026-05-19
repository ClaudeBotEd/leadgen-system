"""Domain exceptions + central FastAPI error handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import get_logger

log = get_logger("errors")


class CouncilError(Exception):
    """Base class for domain-level failures."""

    status_code: int = 500
    code: str = "council_error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class UpstreamModelError(CouncilError):
    """OpenRouter (or any upstream LLM provider) returned an unrecoverable error."""

    status_code = 502
    code = "upstream_model_error"


class ConversationNotFoundError(CouncilError):
    status_code = 404
    code = "conversation_not_found"


class ConfigurationError(CouncilError):
    status_code = 500
    code = "configuration_error"


def _payload(code: str, message: str, details: dict | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    """Attach JSON error handlers that mirror the {error:{code,message,details}} contract."""

    @app.exception_handler(CouncilError)
    async def _council_error_handler(_: Request, exc: CouncilError) -> JSONResponse:
        log.warning("council_error", code=exc.code, message=exc.message, details=exc.details)
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.details or None),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload("http_error", str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_payload(
                "validation_error",
                "Request validation failed.",
                {"errors": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=_payload("internal_error", "An unexpected error occurred."),
        )
