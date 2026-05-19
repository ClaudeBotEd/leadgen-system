"""Sync HTTP client for the llm-council moderation endpoint.

Why sync: lead-radar's pipeline (scrapers + exporter) is sync; moderation
is fanned out via a ThreadPoolExecutor in `moderation.py` for concurrency.
Each worker thread holds one CouncilClient.

This client exposes ONLY moderation. Outreach / sequence generation was
removed in the trust-provenance refactor; the doctrine says the council
must not produce sales copy.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, Optional

import httpx

from .config import ModerationConfig, get_config

log = logging.getLogger("moderation.council_client")


class CouncilClientError(RuntimeError):
    """Raised when the council service returns an unrecoverable error.

    Carries the same classification as the council's own `error_kind`
    (insufficient_credits, unauthorized, invalid_model, rate_limited,
    upstream_5xx, timeout, transport, unexpected, http_error).
    """

    def __init__(self, message: str, *, kind: str = "unknown", status: Optional[int] = None):
        super().__init__(message)
        self.kind = kind
        self.status = status


_RETRY_STATUSES = {408, 425, 429, 500, 502, 503, 504}


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff with jitter: 0.5s, 1.5s, 3.5s, …, capped at 8s."""
    base = min(0.5 * (2 ** attempt), 8.0)
    return base + random.uniform(0, 0.4)


class CouncilClient:
    """Thin, retrying HTTP client for the llm-council moderation surface."""

    def __init__(self, config: Optional[ModerationConfig] = None):
        self.config = config or get_config()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "lead-radar/1.0 moderation-client",
        }
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        self._client = httpx.Client(
            base_url=self.config.council_url,
            headers=headers,
            timeout=self.config.request_timeout_seconds,
        )

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def moderate_lead(
        self,
        candidate: Dict[str, Any],
        *,
        locale: Optional[str] = None,
        strategy: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """POST a captured post to /api/council/moderate-lead.

        Returns the council's verdict body verbatim.
        """
        body: Dict[str, Any] = {
            "candidate": candidate,
            "strategy": strategy or self.config.strategy,
            "locale": locale or self.config.locale,
            "use_cache": use_cache,
        }
        return self._request("POST", "/api/council/moderate-lead", json=body)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CouncilClient":
        return self

    def __exit__(self, *exc):  # noqa: ANN001
        self.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, *, json: Optional[Any] = None) -> Dict[str, Any]:  # noqa: A002
        attempts = max(1, self.config.max_retries + 1)
        last_exc: Optional[Exception] = None
        for attempt in range(attempts):
            try:
                response = self._client.request(method, path, json=json)
                if response.status_code in _RETRY_STATUSES and attempt < attempts - 1:
                    delay = _backoff_seconds(attempt)
                    log.warning(
                        "council_client_retry status=%s attempt=%s delay_s=%.2f",
                        response.status_code,
                        attempt,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                if response.status_code >= 400:
                    raise self._classify(response)
                if not response.content:
                    return {}
                return response.json()
            except httpx.TimeoutException as e:
                last_exc = e
                if attempt < attempts - 1:
                    time.sleep(_backoff_seconds(attempt))
                    continue
                raise CouncilClientError(
                    f"Timed out calling council ({self.config.request_timeout_seconds}s)",
                    kind="timeout",
                ) from e
            except httpx.RequestError as e:
                last_exc = e
                if attempt < attempts - 1:
                    time.sleep(_backoff_seconds(attempt))
                    continue
                raise CouncilClientError(
                    f"Network error calling council: {e}",
                    kind="transport",
                ) from e
        raise CouncilClientError(
            f"Council request exhausted retries: {last_exc}",
            kind="unexpected",
        )

    @staticmethod
    def _classify(response: httpx.Response) -> CouncilClientError:
        status = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = {"detail": response.text[:300]}
        detail = ""
        if isinstance(body, dict):
            detail = str(
                body.get("detail")
                or body.get("message")
                or (body.get("error") or {}).get("message")
                or body
            )
        if status == 401:
            kind = "unauthorized"
        elif status == 402:
            kind = "insufficient_credits"
        elif status == 404:
            kind = "not_found"
        elif status == 429:
            kind = "rate_limited"
        elif 500 <= status < 600:
            kind = "upstream_5xx"
        else:
            kind = "http_error"
        return CouncilClientError(
            f"Council {status}: {detail}".strip(),
            kind=kind,
            status=status,
        )
