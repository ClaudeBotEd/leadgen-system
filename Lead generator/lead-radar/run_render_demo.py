"""CLI: render demo-bundle voor founder-led outreach.

Schrijft naar output/demo/:
  - inventory.html      — huidige inventory snapshot
  - sample-receipt.html — voorbeeld van delivered lead
  - README.md           — usage-note voor Sem

Idempotent: overschrijft bestaande files.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from demo_bundle.inventory_page import render_inventory_html
from demo_bundle.sample_receipt import render_sample_receipt_html


_README_BODY = """\
# Demo-bundle

- `inventory.html`      — huidige inventory snapshot (regenereer met `python3 run_render_demo.py`)
- `sample-receipt.html` — voorbeeld van het delivery-format

Open in browser tijdens een installateur-call.
"""


def render_demo_bundle(
    *,
    inventory_path: str | Path,
    output_dir: str | Path,
    snapshot_at: datetime | None = None,
) -> list[Path]:
    snapshot_at = snapshot_at or datetime.now(timezone.utc)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    inv_path = output_dir / "inventory.html"
    inv_path.write_text(
        render_inventory_html(
            inventory_path=inventory_path,
            snapshot_at=snapshot_at,
        ),
        encoding="utf-8",
    )
    written.append(inv_path)

    receipt_path = output_dir / "sample-receipt.html"
    receipt_path.write_text(render_sample_receipt_html(), encoding="utf-8")
    written.append(receipt_path)

    readme_path = output_dir / "README.md"
    readme_path.write_text(_README_BODY, encoding="utf-8")
    written.append(readme_path)

    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", default="data/lead_inventory.csv")
    parser.add_argument("--output", default="output/demo")
    args = parser.parse_args(argv)

    written = render_demo_bundle(
        inventory_path=args.inventory,
        output_dir=args.output,
    )
    print(f"Wrote {len(written)} files to {args.output}:")
    for p in written:
        print(f"  - {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
