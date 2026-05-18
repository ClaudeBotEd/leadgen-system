"""n8n-ready webhook emitter for qualified leads.

Best-effort POST with a small retry budget. Never raises into the caller —
a broken webhook must not break the scrape pipeline.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx

from .config import IntelligenceConfig, get_config

log = logging.getLogger("intelligence.webhooks")


def _payload(
    lead: Dict[str, Any],
    intelligence: Dict[str, Any],
    sequence: Optional[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compose the JSON sent to n8n (or any webhook listener).

    Stable shape — downstream automations should be safe to depend on it.
    """
    return {
        "event": "lead.qualified",
        "schema_version": 1,
        "lead_id": lead.get("lead_id"),
        "lead": lead,
        "intelligence": intelligence,
        "sequence": sequence,
        "metadata": metadata or {},
    }


def emit_webhook(
    lead: Dict[str, Any],
    intelligence: Dict[str, Any],
    sequence: Optional[Dict[str, Any]] = None,
    *,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[IntelligenceConfig] = None,
) -> bool:
    """Fire the configured webhook. Returns True on 2xx, False otherwise.

    Silent on misconfiguration (no URL) — returns False without logging.
    """
    config = config or get_config()
    if not config.webhook_url:
        return False
    score = int(intelligence.get("lead_quality_score") or 0)
    if score < config.webhook_min_score:
        return False

    payload = _payload(lead, intelligence, sequence, metadata)
    last_error: Optional[str] = None
    for attempt in range(max(1, config.max_retries + 1)):
        try:
            r = httpx.post(
                config.webhook_url,
                json=payload,
                timeout=min(config.request_timeout_seconds, 15.0),
                headers={"User-Agent": "lead-radar/1.0 webhook"},
            )
            if 200 <= r.status_code < 300:
                log.info(
                    "webhook_emitted status=%s lead_id=%s score=%s",
                    r.status_code,
                    lead.get("lead_id"),
                    score,
                )
                return True
            last_error = f"HTTP {r.status_code}: {r.text[:200]}"
        except httpx.RequestError as e:
            last_error = f"{type(e).__name__}: {e}"
        if attempt < config.max_retries:
            time.sleep(0.5 * (2 ** attempt))

    log.warning(
        "webhook_failed lead_id=%s error=%s",
        lead.get("lead_id"),
        last_error,
    )
    return False
