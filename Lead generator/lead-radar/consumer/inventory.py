"""Inventory pool — warme voorraad van APPROVED leads die nog niet DELIVERED zijn.

Plan A foundation module. Houdt CSV-schema, append-helpers en
expire-sweep functies. Wordt gebruikt door Plan B's approval-flow
(console writes inventory rows) en door de nightly sweep CLI.

Inventory is geen vervanging van pcs.py's event-log; het is een
parallelle "warme voorraad" view. EXPIRED-transities worden via
pcs.append_transition naar lead_log.csv geschreven (single source
of truth voor state changes).
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

import pcs


INVENTORY_FIELDS: list[str] = [
    "lead_id",
    "niche",
    "region_nl",
    "intent_strength",
    "captured_at",
    "approved_at",
    "expires_at",
    "source_class",
    "reviewer_attestation",
    "delivered_to",
    "demo_used_at",
    "still_warm_checked_at",
]


def ensure_inventory_csv(path: str | Path) -> Path:
    """Maakt lead_inventory.csv aan met de juiste header indien afwezig.

    Idempotent: bestaande bestanden met de juiste header worden niet aangeraakt.
    Raises ValueError als een bestaande file een andere header heeft (geen
    silent acceptance van schema-drift).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=INVENTORY_FIELDS)
            writer.writeheader()
        return path
    # Existing file: validate header
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, [])
    if header != INVENTORY_FIELDS:
        raise ValueError(
            f"{path.name} header mismatch: expected {INVENTORY_FIELDS}, got {header}"
        )
    return path


VALID_INTENT_STRENGTHS = frozenset({"HOT", "WARM"})
VALID_SOURCE_CLASSES = frozenset({"apify_public", "burner_closed", "paste"})


def append_inventory_row(
    path: str | Path,
    *,
    lead_id: str,
    niche: str,
    region_nl: str,
    intent_strength: str,
    captured_at: str,
    approved_at: str,
    expires_at: str,
    source_class: str,
    reviewer_attestation: str = "",
    delivered_to: str = "",
    demo_used_at: str = "",
    still_warm_checked_at: str = "",
) -> Path:
    """Append een row aan lead_inventory.csv.

    Valideert intent_strength en source_class tegen toegestane waarden.
    """
    if intent_strength not in VALID_INTENT_STRENGTHS:
        raise ValueError(
            f"intent_strength must be one of {sorted(VALID_INTENT_STRENGTHS)}, "
            f"got {intent_strength!r}"
        )
    if source_class not in VALID_SOURCE_CLASSES:
        raise ValueError(
            f"source_class must be one of {sorted(VALID_SOURCE_CLASSES)}, "
            f"got {source_class!r}"
        )

    path = ensure_inventory_csv(path)
    with Path(path).open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INVENTORY_FIELDS)
        writer.writerow({
            "lead_id": lead_id,
            "niche": niche,
            "region_nl": region_nl,
            "intent_strength": intent_strength,
            "captured_at": captured_at,
            "approved_at": approved_at,
            "expires_at": expires_at,
            "source_class": source_class,
            "reviewer_attestation": reviewer_attestation,
            "delivered_to": delivered_to,
            "demo_used_at": demo_used_at,
            "still_warm_checked_at": still_warm_checked_at,
        })
    return Path(path)


def load_decay_windows(config_path: str | Path) -> dict[str, dict[str, int]]:
    """Laad decay-windows uit config.yaml.

    Schema: inventory.decay_windows.<niche>.<HOT|WARM> = aantal dagen.

    Raises KeyError als de inventory sectie ontbreekt.
    """
    config_path = Path(config_path)
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if "inventory" not in data:
        raise KeyError("config.yaml missing 'inventory' section")
    return data["inventory"].get("decay_windows", {})


def compute_expires_at(
    captured_at: datetime,
    niche: str,
    intent_strength: str,
    decay_windows: dict[str, dict[str, int]],
) -> datetime:
    """Bereken expires_at als captured_at + decay_windows[niche][intent_strength] dagen.

    Raises KeyError als niche of intent_strength niet in decay_windows zitten.
    """
    if niche not in decay_windows:
        raise KeyError(f"niche {niche!r} not in decay_windows")
    niche_windows = decay_windows[niche]
    if intent_strength not in niche_windows:
        raise KeyError(
            f"intent_strength {intent_strength!r} not in decay_windows[{niche!r}]"
        )
    days = niche_windows[intent_strength]
    return captured_at + timedelta(days=days)


def sweep_expired_inventory(
    *,
    inventory_path: str | Path,
    lead_log_path: str | Path,
    actor: str = "cron",
    now: datetime | None = None,
) -> list[str]:
    """Vind leads met expires_at < now en die nog niet DELIVERED zijn.

    Schrijft per overdue lead een EXPIRED-transitie naar lead_log_path
    via pcs.append_transition. Idempotent: als er al een EXPIRED-rij
    bestaat voor dit lead_id, wordt 'm overgeslagen.

    **Not safe for concurrent callers.** Two parallel sweeps can both
    read 'no expired yet' and both write EXPIRED rows for the same lead.
    The CLI wrapper (run_inventory_sweep.py) is the only intended caller;
    serialize via a process-level lock if running outside the wrapper.

    Naive (timezone-less) ISO strings in expires_at are treated as UTC.

    Returns: lijst van expired lead_ids (in volgorde).
    """
    now = now or datetime.now(timezone.utc)
    inventory_path = Path(inventory_path)
    lead_log_path = Path(lead_log_path)

    if not inventory_path.exists():
        return []

    already_expired: set[str] = set()
    if lead_log_path.exists():
        with lead_log_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("to_state") == "EXPIRED":
                    already_expired.add(row["lead_id"])

    expired_now: list[str] = []
    with inventory_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lead_id = row["lead_id"]
            if lead_id in already_expired:
                continue
            if row.get("delivered_to"):
                continue
            expires_at_str = row.get("expires_at", "")
            if not expires_at_str:
                continue
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if expires_at < now:
                expired_now.append(lead_id)

    for lead_id in expired_now:
        pcs.append_transition(
            lead_id,
            from_state="APPROVED",
            to_state="EXPIRED",
            actor=actor,
            reason="inventory_sweep:decay_window_passed",
            log_path=lead_log_path,
        )

    return expired_now
