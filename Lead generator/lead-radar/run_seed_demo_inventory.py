"""CLI: seed synthetische demo-leads naar inventory voor founder-rehearsal.

Idempotent: leads waarvan lead_id al bestaat in inventory worden
overgeslagen. Schrijft GEEN lead_log transitions — dit is een demo-
preseed, niet een echt approve-pad.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from consumer.inventory import (
    append_inventory_row,
    compute_expires_at,
    ensure_inventory_csv,
    load_decay_windows,
)


_NOW = datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc)


DEMO_LEADS: list[dict] = [
    {
        "lead_id": "demo-wp-utr-001",
        "niche": "warmtepomp",
        "region_nl": "utrecht|amersfoort",
        "intent_strength": "HOT",
        "captured_at": _NOW - timedelta(hours=6),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-wp-utr-002",
        "niche": "warmtepomp",
        "region_nl": "utrecht|utrecht",
        "intent_strength": "WARM",
        "captured_at": _NOW - timedelta(days=2),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-zp-utr-001",
        "niche": "zonnepanelen",
        "region_nl": "utrecht|amersfoort",
        "intent_strength": "HOT",
        "captured_at": _NOW - timedelta(days=1),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-zp-flv-001",
        "niche": "zonnepanelen",
        "region_nl": "flevoland|almere",
        "intent_strength": "WARM",
        "captured_at": _NOW - timedelta(days=3),
        "source_class": "burner_closed",
        "reviewer_attestation": "Lid sinds 2024; observerend account",
    },
    {
        "lead_id": "demo-iso-utr-001",
        "niche": "isolatie",
        "region_nl": "utrecht|nieuwegein",
        "intent_strength": "HOT",
        "captured_at": _NOW - timedelta(hours=18),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-airco-utr-001",
        "niche": "airco",
        "region_nl": "utrecht|veenendaal",
        "intent_strength": "WARM",
        "captured_at": _NOW - timedelta(days=4),
        "source_class": "burner_closed",
        "reviewer_attestation": "Lid sinds 2023; meelees-rol",
    },
    {
        "lead_id": "demo-lp-utr-001",
        "niche": "laadpaal",
        "region_nl": "utrecht|amersfoort",
        "intent_strength": "HOT",
        "captured_at": _NOW - timedelta(hours=3),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
    {
        "lead_id": "demo-dak-flv-001",
        "niche": "dakwerk",
        "region_nl": "flevoland|lelystad",
        "intent_strength": "WARM",
        "captured_at": _NOW - timedelta(days=2),
        "source_class": "apify_public",
        "reviewer_attestation": "",
    },
]


def seed_demo_inventory(
    *,
    inventory_path: str | Path,
    decay_windows: dict[str, dict[str, int]],
) -> int:
    inventory_path = Path(inventory_path)
    ensure_inventory_csv(inventory_path)

    existing_ids: set[str] = set()
    with inventory_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            existing_ids.add(row["lead_id"])

    written = 0
    for lead in DEMO_LEADS:
        if lead["lead_id"] in existing_ids:
            continue
        captured_at = lead["captured_at"]
        expires_at = compute_expires_at(
            captured_at, lead["niche"], lead["intent_strength"], decay_windows
        )
        append_inventory_row(
            inventory_path,
            lead_id=lead["lead_id"],
            niche=lead["niche"],
            region_nl=lead["region_nl"],
            intent_strength=lead["intent_strength"],
            captured_at=captured_at.isoformat(timespec="seconds"),
            approved_at=captured_at.isoformat(timespec="seconds"),
            expires_at=expires_at.isoformat(timespec="seconds"),
            source_class=lead["source_class"],
            reviewer_attestation=lead["reviewer_attestation"],
        )
        written += 1
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", default="data/lead_inventory.csv")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)

    decay_windows = load_decay_windows(args.config)
    n = seed_demo_inventory(
        inventory_path=args.inventory, decay_windows=decay_windows
    )
    print(f"Seeded {n} demo lead(s) into {args.inventory}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
