"""CLI: export one reviewed lead as a standalone HTML receipt.

Reads a JSONL file containing reviewed leads, selects one row by lead_id,
routes it through the existing delivery routing logic, renders with the
existing HTML receipt renderer, and writes exactly one HTML file.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from delivery.case_id import generate_case_id, next_sequence_for_date
from delivery.model import ReviewedLead, RoutedLead
from delivery.render_html import render_html
from delivery.route import load_installers, pick_installer


def load_reviewed_lead(input_path: str | Path, lead_id: str) -> ReviewedLead:
    path = Path(input_path)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if str(raw.get("lead_id", "")) == lead_id:
                return ReviewedLead.from_dict(raw)
    raise ValueError(f"lead_id {lead_id!r} not found in {path}")


def export_receipt(
    *,
    input_path: str | Path,
    lead_id: str,
    output_path: str | Path,
    installers_path: str | Path = "data/installers.csv",
    lead_log_path: str | Path = "data/lead_log.csv",
    now: datetime | None = None,
) -> Path:
    now = now or datetime.now(timezone.utc)
    reviewed = load_reviewed_lead(input_path, lead_id)
    installers = load_installers(installers_path)
    installer = pick_installer(reviewed, installers, log_path=lead_log_path)
    if installer is None:
        raise ValueError(
            f"No active installer route found for lead_id {lead_id!r} "
            f"(region={reviewed.region!r}, niche={reviewed.niche!r})"
        )

    sequence = next_sequence_for_date(now.date(), log_path=lead_log_path)
    case_id = generate_case_id(now.date(), sequence)
    routed = RoutedLead(
        reviewed_lead=reviewed,
        installer=installer,
        case_id=case_id,
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_html(routed, now=now), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Reviewed-leads JSONL path")
    parser.add_argument("--lead-id", required=True, help="lead_id to render")
    parser.add_argument("--output", required=True, help="HTML output path")
    parser.add_argument(
        "--installers",
        default="data/installers.csv",
        help="Installer registry CSV path",
    )
    parser.add_argument(
        "--lead-log",
        default="data/lead_log.csv",
        help="Lead log CSV path for exclusivity and case sequencing",
    )
    args = parser.parse_args(argv)

    try:
        written = export_receipt(
            input_path=args.input,
            lead_id=args.lead_id,
            output_path=args.output,
            installers_path=args.installers,
            lead_log_path=args.lead_log,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote receipt: {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
