"""JSONL-based CRM store for qualified leads.

One JSON object per line at `data/crm/qualified_leads.jsonl`.

Schema (schema_version=1):
    {
      "saved_at":    "2026-05-18T12:34:56.123Z",        # ISO-8601 UTC
      "lead_id":     "lr_00001",
      "lead":        { ... raw scraped lead fields ... },
      "intelligence":{ ... 13-field score dict ... },
      "sequence":    { ... outreach drafts ... } | null,
      "metadata": {
        "threshold":      6,
        "strategy":       "fast",
        "schema_version": 1,
        ...caller-provided extras...
      }
    }

Append-only, line-delimited so n8n / log shippers can tail it.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import IntelligenceConfig, get_config

_LOCK = threading.Lock()


def qualified_path(config: Optional[IntelligenceConfig] = None) -> Path:
    config = config or get_config()
    return config.crm_path


def _now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + now.strftime("%f")[:3] + "Z"


def save_qualified(
    lead: Dict[str, Any],
    intelligence: Dict[str, Any],
    sequence: Optional[Dict[str, Any]],
    *,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[IntelligenceConfig] = None,
) -> Path:
    """Append a qualified lead to the CRM JSONL store.

    Thread-safe (process-local lock + atomic append). Returns the path
    that was written to.
    """
    config = config or get_config()
    path = config.crm_path
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "saved_at": _now_iso(),
        "lead_id": lead.get("lead_id") or intelligence.get("lead_id"),
        "lead": lead,
        "intelligence": intelligence,
        "sequence": sequence,
        "metadata": {
            "threshold": config.quality_threshold,
            "strategy": config.score_strategy,
            "schema_version": 1,
            **(metadata or {}),
        },
    }
    line = json.dumps(record, ensure_ascii=False, default=str)
    with _LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    return path
