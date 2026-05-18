"""Case-id generator. LR-YYYY-MM-DD-NNNN, sequence per delivery date.

Sequence comes from counting prior APPROVED -> DELIVERED transitions in
data/lead_log.csv whose `at` falls on the same UTC date. New leads get
sequence = count + 1. Max sequence per day is 9999.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Union

DEFAULT_LOG_PATH = Path("data/lead_log.csv")


def generate_case_id(delivery_date: date, sequence: int) -> str:
    if sequence < 1:
        raise ValueError(f"sequence must be >= 1, got {sequence}")
    if sequence > 9999:
        raise ValueError(f"sequence {sequence} exceeds 9999 (per-day max)")
    return f"LR-{delivery_date.isoformat()}-{sequence:04d}"


def next_sequence_for_date(
    delivery_date: date,
    log_path: Union[str, Path] = DEFAULT_LOG_PATH,
) -> int:
    path = Path(log_path)
    if not path.exists():
        return 1
    count = 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("to_state") != "DELIVERED":
                continue
            at_raw = row.get("at", "")
            try:
                at = datetime.fromisoformat(at_raw)
            except ValueError:
                continue
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            if at.astimezone(timezone.utc).date() == delivery_date:
                count += 1
    return count + 1
