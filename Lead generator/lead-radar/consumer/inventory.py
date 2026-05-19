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
from pathlib import Path


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

    Idempotent: bestaande bestanden worden niet aangeraakt.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size == 0:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=INVENTORY_FIELDS)
            writer.writeheader()
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
