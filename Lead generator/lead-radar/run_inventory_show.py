"""CLI: print huidige inventory als leesbare terminal-tabel.

Voor founder-rehearsal en operational orientation. Geen filtering,
geen sorting flags V0 — alle rows in CSV-volgorde.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


_COLUMNS = [
    ("lead_id", 22),
    ("niche", 14),
    ("region_nl", 22),
    ("intent", 6),
    ("captured", 12),
    ("expires", 12),
    ("source", 14),
]


def _truncate(value: str, width: int) -> str:
    if len(value) <= width:
        return value.ljust(width)
    return (value[: width - 1] + "…").ljust(width)


def render_inventory_table(path: str | Path) -> str:
    path = Path(path)
    if not path.exists():
        return "Geen inventory gevonden op " + str(path)

    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return "Geen inventory rows (alleen header)."

    header = " ".join(_truncate(name, width) for name, width in _COLUMNS)
    rule = "-" * len(header)
    lines = [header, rule]
    for row in rows:
        captured = (row.get("captured_at") or "")[:10]
        expires = (row.get("expires_at") or "")[:10]
        cells = [
            _truncate(row.get("lead_id", ""), 22),
            _truncate(row.get("niche", ""), 14),
            _truncate(row.get("region_nl", ""), 22),
            _truncate(row.get("intent_strength", ""), 6),
            _truncate(captured, 12),
            _truncate(expires, 12),
            _truncate(row.get("source_class", ""), 14),
        ]
        lines.append(" ".join(cells))
    lines.append(rule)
    lines.append(f"{len(rows)} lead(s) in pool.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", default="data/lead_inventory.csv")
    args = parser.parse_args(argv)
    print(render_inventory_table(args.inventory))
    return 0


if __name__ == "__main__":
    sys.exit(main())
