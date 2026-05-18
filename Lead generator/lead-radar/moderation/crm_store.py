"""Append-only approved-lead store (replaces the old `qualified` CRM store).

One JSON object per line at `data/moderation/approved_leads.jsonl`.

Schema (schema_version=2 — provenance-aligned):

    {
      "saved_at":     "2026-05-18T13:24:55.123Z",          # ISO-8601 UTC, ms precision
      "candidate_id": "cap_00001",
      "candidate":    { ... raw captured-post fields ... }, # provenance trail
      "review":       { ...14-field LeadReview dict... },   # council verdict
      "approval": {
        "approved":          true | false,
        "reason":            human-readable string,
        "approved_temperatures": ["HOT"],
        "min_confidence_band":   "high",
        "require_provenance":   ["verified"]
      },
      "metadata": {
        "strategy":       "fast" | "council",
        "model":          "openai/gpt-4.1",
        "schema_version": 2,
        ...caller-provided extras...
      }
    }

Append-only, line-delimited so n8n / log shippers can tail it. Only
records that clear the moderation-config approval gate are written here
— anything below the gate is captured in run_results.jsonl instead.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import ModerationConfig, get_config

_LOCK = threading.Lock()

_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


def approved_path(config: Optional[ModerationConfig] = None) -> Path:
    config = config or get_config()
    return config.approved_path


def _now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + now.strftime("%f")[:3] + "Z"


def evaluate_approval(
    review: Dict[str, Any],
    config: Optional[ModerationConfig] = None,
) -> Dict[str, Any]:
    """Decide whether a moderation review clears the approval gate.

    Returns {"approved": bool, "reason": str, ...thresholds in effect...}.
    """
    config = config or get_config()
    temperature = (review.get("lead_temperature") or "").upper()
    confidence = (review.get("confidence_band") or "").lower()
    provenance = (review.get("provenance_status") or "").lower()
    trust_flags = review.get("trust_flags") or []
    review_required = bool(review.get("review_required"))

    reasons: List[str] = []
    if temperature not in config.approved_temperatures:
        reasons.append(f"temperature {temperature!r} not in {list(config.approved_temperatures)}")
    min_rank = _CONFIDENCE_ORDER.get(config.min_confidence_band, 2)
    if _CONFIDENCE_ORDER.get(confidence, -1) < min_rank:
        reasons.append(
            f"confidence_band {confidence!r} < required {config.min_confidence_band!r}"
        )
    if provenance not in config.require_provenance:
        reasons.append(
            f"provenance_status {provenance!r} not in {list(config.require_provenance)}"
        )
    if trust_flags:
        reasons.append(f"trust_flags present: {trust_flags}")
    if review_required:
        reasons.append("review_required=True (council not confident enough to clear)")

    approved = not reasons
    return {
        "approved": approved,
        "reason": "approved" if approved else "; ".join(reasons),
        "approved_temperatures": list(config.approved_temperatures),
        "min_confidence_band": config.min_confidence_band,
        "require_provenance": list(config.require_provenance),
    }


def save_approved(
    candidate: Dict[str, Any],
    review: Dict[str, Any],
    *,
    approval: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[ModerationConfig] = None,
) -> Path:
    """Append an APPROVED record to the moderation store.

    The caller is expected to have already checked `evaluate_approval`.
    Thread-safe (process-local lock + atomic append).
    """
    config = config or get_config()
    path = config.approved_path
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "saved_at": _now_iso(),
        "candidate_id": candidate.get("candidate_id") or review.get("candidate_id"),
        "candidate": candidate,
        "review": review,
        "approval": approval or evaluate_approval(review, config),
        "metadata": {
            "strategy": config.strategy,
            "schema_version": 2,
            **(metadata or {}),
        },
    }
    line = json.dumps(record, ensure_ascii=False, default=str)
    with _LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return path
