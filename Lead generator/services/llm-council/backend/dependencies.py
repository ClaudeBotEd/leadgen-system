"""FastAPI dependencies: rate-limit handle + optional bearer-token gate."""

from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import get_settings


def _client_key(request: Request) -> str:
    """Prefer the API token (if set) over IP so n8n/CRM share a key, not all IPs."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1][:32]
    return get_remote_address(request)


limiter = Limiter(key_func=_client_key)


async def require_api_token(
    authorization: Optional[str] = Header(default=None),
) -> None:
    """When LLM_COUNCIL_API_TOKEN is set, require a matching Bearer token.

    Leave the env empty in development to disable auth.
    """
    settings = get_settings()
    if not settings.api_token:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token.",
        )


__all__ = ["limiter", "require_api_token"]
