"""Env-driven config for the moderation layer.

All keys are prefixed LEAD_RADAR_MODERATION_* (renamed from the legacy
LEAD_RADAR_INTELLIGENCE_* during the trust-provenance refactor).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or not v.strip():
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    v = os.getenv(key)
    if v is None or not v.strip():
        return default
    try:
        return float(v)
    except ValueError:
        return default


HERE = Path(__file__).resolve().parent.parent
DEFAULT_APPROVED_PATH = HERE / "data" / "moderation" / "approved_leads.jsonl"


@dataclass(frozen=True)
class ModerationConfig:
    """Resolved configuration for the lead-radar moderation layer.

    Approval gate (doctrine §00.2, §01.5): an approved lead must clear:
      - lead_temperature in `approved_temperatures` (default {HOT})
      - confidence_band >= `min_confidence_band` (default high)
      - provenance_status in `require_provenance` (default {verified})
      - trust_flags is empty
      - review_required is False
    Anything else is recorded in run_results.jsonl but does NOT enter
    the approved store and never fires the webhook.
    """

    enabled: bool
    council_url: str
    api_token: Optional[str]
    request_timeout_seconds: float
    max_retries: int
    max_concurrent: int
    strategy: str          # "fast" | "council"
    locale: str

    approved_temperatures: Tuple[str, ...]
    min_confidence_band: str          # "high" | "medium" | "low"
    require_provenance: Tuple[str, ...]

    approved_path: Path

    webhook_url: Optional[str]
    webhook_event: str                 # default "lead.approved"

    fail_open: bool                    # if council unreachable, skip rather than crash


def get_config() -> ModerationConfig:
    approved_path_str = (
        os.getenv("LEAD_RADAR_MODERATION_APPROVED_PATH")
        or str(DEFAULT_APPROVED_PATH)
    )
    approved_temps = tuple(
        s.strip().upper()
        for s in os.getenv("LEAD_RADAR_MODERATION_APPROVED_TEMPERATURES", "HOT").split(",")
        if s.strip()
    )
    require_provenance = tuple(
        s.strip().lower()
        for s in os.getenv("LEAD_RADAR_MODERATION_REQUIRE_PROVENANCE", "verified").split(",")
        if s.strip()
    )
    return ModerationConfig(
        enabled=_env_bool("LEAD_RADAR_MODERATION_ENABLED", default=False),
        council_url=os.getenv(
            "LEAD_RADAR_MODERATION_COUNCIL_URL", "http://localhost:8001"
        ).rstrip("/"),
        api_token=os.getenv("LEAD_RADAR_MODERATION_API_TOKEN") or None,
        request_timeout_seconds=_env_float("LEAD_RADAR_MODERATION_TIMEOUT", 60.0),
        max_retries=_env_int("LEAD_RADAR_MODERATION_MAX_RETRIES", 2),
        max_concurrent=_env_int("LEAD_RADAR_MODERATION_MAX_CONCURRENT", 4),
        strategy=(os.getenv("LEAD_RADAR_MODERATION_STRATEGY", "fast") or "fast").lower(),
        locale=os.getenv("LEAD_RADAR_MODERATION_LOCALE", "nl"),
        approved_temperatures=approved_temps or ("HOT",),
        min_confidence_band=(
            os.getenv("LEAD_RADAR_MODERATION_MIN_CONFIDENCE", "high") or "high"
        ).lower(),
        require_provenance=require_provenance or ("verified",),
        approved_path=Path(approved_path_str),
        webhook_url=os.getenv("LEAD_RADAR_MODERATION_WEBHOOK_URL") or None,
        webhook_event=os.getenv("LEAD_RADAR_MODERATION_WEBHOOK_EVENT", "lead.approved"),
        fail_open=_env_bool("LEAD_RADAR_MODERATION_FAIL_OPEN", default=True),
    )
