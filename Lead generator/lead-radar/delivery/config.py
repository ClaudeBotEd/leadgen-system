"""Env-driven delivery config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}


@dataclass
class DeliveryConfig:
    reply_domain: str
    dry_run: bool = True
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    decay_days: int = 8
    input_path: Path = Path("data/reviewed/approved.jsonl")
    installers_path: Path = Path("data/installers.csv")
    log_path: Path = Path("data/lead_log.csv")
    audit_path: Path = Path("data/delivery_log.jsonl")


def load_config() -> DeliveryConfig:
    reply_domain = os.environ.get("DELIVERY_REPLY_DOMAIN", "").strip()
    if not reply_domain:
        raise ValueError("DELIVERY_REPLY_DOMAIN must be set")

    dry_run = _bool("DELIVERY_DRY_RUN", default=True)
    smtp_host = os.environ.get("DELIVERY_SMTP_HOST")
    smtp_user = os.environ.get("DELIVERY_SMTP_USER")
    smtp_password = os.environ.get("DELIVERY_SMTP_PASSWORD")

    if not dry_run:
        if not (smtp_host and smtp_user and smtp_password):
            raise ValueError(
                "SMTP credentials (DELIVERY_SMTP_HOST/USER/PASSWORD) required when DELIVERY_DRY_RUN=false"
            )

    return DeliveryConfig(
        reply_domain=reply_domain,
        dry_run=dry_run,
        smtp_host=smtp_host,
        smtp_port=int(os.environ.get("DELIVERY_SMTP_PORT", "587")),
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        smtp_use_tls=_bool("DELIVERY_SMTP_USE_TLS", default=True),
        decay_days=int(os.environ.get("DELIVERY_DECAY_DAYS", "8")),
        input_path=Path(os.environ.get("DELIVERY_INPUT_PATH", "data/reviewed/approved.jsonl")),
        installers_path=Path(os.environ.get("DELIVERY_INSTALLERS_PATH", "data/installers.csv")),
        log_path=Path(os.environ.get("DELIVERY_LOG_PATH", "data/lead_log.csv")),
        audit_path=Path(os.environ.get("DELIVERY_AUDIT_PATH", "data/delivery_log.jsonl")),
    )
