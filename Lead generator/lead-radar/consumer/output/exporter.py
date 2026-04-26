"""Exporter — schrijft Lead lijst naar CSV en JSON.

Bestandsnamen: `leads_<niche>_<YYYY-MM-DD>.csv|json`
Pad: `<outdir>/data/leads/consumer/`  (default als geen outdir gegeven).

CSV is breed (alle velden) maar de spec-velden komen eerst zodat
spreadsheet-tools er meteen mee werken.
"""
from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from .. import Lead

log = logging.getLogger("consumer.output.exporter")

CSV_FIELDS = [
    "id", "source", "niche", "score", "intent", "city",
    "title", "summary", "text", "url", "author",
    "created_at", "captured_at", "breakdown",
]


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def export_leads(leads: list[Lead], *, niche: str, outdir: Path | str | None = None,
                 also_json: bool = True) -> dict[str, Path]:
    """Schrijf leads naar CSV (en optioneel JSON).

    Returns dict met paden: {'csv': ..., 'json': ...}.  Maakt dirs aan.
    Sorteert op score desc.
    """
    base = Path(outdir) if outdir else Path(__file__).resolve().parents[2] / "data" / "leads" / "consumer"
    base.mkdir(parents=True, exist_ok=True)

    leads_sorted = sorted(leads, key=lambda l: l.score, reverse=True)
    date = _today()
    csv_path = base / f"leads_{niche}_{date}.csv"
    json_path = base / f"leads_{niche}_{date}.json"

    try:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for lead in leads_sorted:
                row = lead.to_dict()
                row["breakdown"] = json.dumps(lead.breakdown, ensure_ascii=False)
                writer.writerow(row)
        log.info("CSV geschreven: %s (%d leads)", csv_path, len(leads_sorted))
    except Exception as e:
        log.error("CSV schrijven faalde: %s", e)

    paths: dict[str, Path] = {"csv": csv_path}
    if also_json:
        try:
            json_path.write_text(
                json.dumps([l.to_dict() for l in leads_sorted], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            log.info("JSON geschreven: %s", json_path)
            paths["json"] = json_path
        except Exception as e:
            log.error("JSON schrijven faalde: %s", e)

    return paths
