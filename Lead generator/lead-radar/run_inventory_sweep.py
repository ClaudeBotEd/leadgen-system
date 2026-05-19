"""CLI wrapper voor sweep_expired_inventory.

Usage:
    python3 run_inventory_sweep.py [--inventory PATH] [--lead-log PATH] [--dry-run]

Default paden: data/lead_inventory.csv en data/lead_log.csv (relatief aan
het lead-radar/ project root).

Voor automation via launchd: zie com.leadradar.inventory_sweep.plist.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from consumer.inventory import sweep_expired_inventory


def _dry_run_preview(inventory_path: Path, lead_log_path: Path) -> list[str]:
    """Zonder schrijven: welke lead_ids zouden expired worden."""
    now = datetime.now(timezone.utc)
    if not inventory_path.exists():
        return []

    already_expired: set[str] = set()
    if lead_log_path.exists():
        with lead_log_path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("to_state") == "EXPIRED":
                    already_expired.add(row["lead_id"])

    candidates: list[str] = []
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
                candidates.append(lead_id)
    return candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        default="data/lead_inventory.csv",
        help="Path naar inventory CSV (default: data/lead_inventory.csv)",
    )
    parser.add_argument(
        "--lead-log",
        default="data/lead_log.csv",
        help="Path naar lead_log CSV (default: data/lead_log.csv)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Toon wat geexpired zou worden zonder te schrijven",
    )
    args = parser.parse_args(argv)

    inventory_path = Path(args.inventory)
    lead_log_path = Path(args.lead_log)

    if args.dry_run:
        candidates = _dry_run_preview(inventory_path, lead_log_path)
        print(f"DRY-RUN: {len(candidates)} expired candidates")
        for lead_id in candidates:
            print(f"  - {lead_id}")
        return 0

    expired = sweep_expired_inventory(
        inventory_path=inventory_path,
        lead_log_path=lead_log_path,
        actor="cron",
    )
    print(f"Sweep complete: {len(expired)} expired")
    for lead_id in expired:
        print(f"  - {lead_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
