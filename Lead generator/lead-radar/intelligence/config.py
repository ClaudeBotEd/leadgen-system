"""Env-driven config for the AI intelligence layer.

All keys are prefixed LEAD_RADAR_INTELLIGENCE_* so they're discoverable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
DEFAULT_CRM_PATH = HERE / "data" / "crm" / "qualified_leads.jsonl"


@dataclass(frozen=True)
class IntelligenceConfig:
    """Resolved configuration for the lead-radar intelligence layer."""

    enabled: bool
    council_url: str
    api_token: Optional[str]
    request_timeout_seconds: float
    max_retries: int
    max_concurrent: int
    score_strategy: str  # "fast" | "council"
    generate_sequence: bool
    locale: str
    quality_threshold: int  # 0-10 inclusive; leads below this are NOT saved
    crm_path: Path
    webhook_url: Optional[str]
    webhook_min_score: int  # only fire webhook for leads at or above this
    fail_open: bool  # if council is unreachable, keep the run going (just skip enrich)


def get_config() -> IntelligenceConfig:
    crm_path_str = os.getenv("LEAD_RADAR_INTELLIGENCE_CRM_PATH") or str(DEFAULT_CRM_PATH)
    return IntelligenceConfig(
        enabled=_env_bool("LEAD_RADAR_INTELLIGENCE_ENABLED", default=False),
        council_url=os.getenv(
            "LEAD_RADAR_INTELLIGENCE_COUNCIL_URL", "http://localhost:8001"
        ).rstrip("/"),
        api_token=os.getenv("LEAD_RADAR_INTELLIGENCE_API_TOKEN") or None,
        request_timeout_seconds=_env_float("LEAD_RADAR_INTELLIGENCE_TIMEOUT", 60.0),
        max_retries=_env_int("LEAD_RADAR_INTELLIGENCE_MAX_RETRIES", 2),
        max_concurrent=_env_int("LEAD_RADAR_INTELLIGENCE_MAX_CONCURRENT", 4),
        score_strategy=(os.getenv("LEAD_RADAR_INTELLIGENCE_STRATEGY", "fast") or "fast").lower(),
        generate_sequence=_env_bool("LEAD_RADAR_INTELLIGENCE_GENERATE_SEQUENCE", default=True),
        locale=os.getenv("LEAD_RADAR_INTELLIGENCE_LOCALE", "en"),
        quality_threshold=_env_int("LEAD_RADAR_INTELLIGENCE_QUALITY_THRESHOLD", 6),
        crm_path=Path(crm_path_str),
        webhook_url=os.getenv("LEAD_RADAR_INTELLIGENCE_WEBHOOK_URL") or None,
        webhook_min_score=_env_int("LEAD_RADAR_INTELLIGENCE_WEBHOOK_MIN_SCORE", 7),
        fail_open=_env_bool("LEAD_RADAR_INTELLIGENCE_FAIL_OPEN", default=True),
    )
