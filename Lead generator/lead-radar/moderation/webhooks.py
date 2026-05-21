"""n8n-ready webhook emitter for approved leads.

Best-effort POST with a small retry budget. Never raises into the caller —
a broken webhook must not break the scrape pipeline.

Doctrine: webhooks only fire for records that have already cleared the
approval gate (HOT + high confidence + verified provenance + no flags +
not review_required). The webhook caller does NOT re-implement the gate.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx

from .config import ModerationConfig, get_config

log = logging.getLogger("moderation.webhooks")


def _payload(
    candidate: Dict[str, Any],
    review: Dict[str, Any],
    approval: Optional[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]],
    event: str,
) -> Dict[str, Any]:
    """Compose the JSON sent to n8n (or any webhook listener).

    Stable shape — downstream automations should be safe to depend on it.
    """
    return {
        "event": event,
        "schema_version": 2,
        "candidate_id": candidate.get("candidate_id"),
        "candidate": candidate,
        "review": review,
        "approval": approval or {},
        "metadata": metadata or {},
    }


def emit_webhook(
    candidate: Dict[str, Any],
    review: Dict[str, Any],
    *,
    approval: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[ModerationConfig] = None,
) -> bool:
    """Fire the configured webhook for an approved lead.

    Returns True on 2xx, False otherwise. Silent on misconfiguration
    (no URL) — returns False without logging.
    """
    config = config or get_config()
    if not config.webhook_url:
        return False

    payload = _payload(candidate, review, approval, metadata, config.webhook_event)
    last_error: Optional[str] = None
    for attempt in range(max(1, config.max_retries + 1)):
        try:
            r = httpx.post(
                config.webhook_url,
                json=payload,
                timeout=min(config.request_timeout_seconds, 15.0),
                headers={"User-Agent": "lead-radar/1.0 moderation-webhook"},
            )
            if 200 <= r.status_code < 300:
                log.info(
                    "webhook_emitted status=%s candidate_id=%s event=%s",
                    r.status_code,
                    candidate.get("candidate_id"),
                    config.webhook_event,
                )
                return True
            last_error = f"HTTP {r.status_code}: {r.text[:200]}"
        except httpx.RequestError as e:
            last_error = f"{type(e).__name__}: {e}"
        if attempt < config.max_retries:
            time.sleep(0.5 * (2 ** attempt))

    log.warning(
        "webhook_failed candidate_id=%s error=%s",
        candidate.get("candidate_id"),
        last_error,
    )
    return False
