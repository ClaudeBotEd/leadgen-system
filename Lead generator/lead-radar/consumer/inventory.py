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
