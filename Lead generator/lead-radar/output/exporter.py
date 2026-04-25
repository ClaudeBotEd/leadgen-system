"""Output exporters — CSV en JSON.

Schrijft leads naar `data/leads_<niche>_<location>_<YYYYMMDD>.csv|json`.
Vaste kolomvolgorde voor compatibiliteit met crm-light en outreach.
"""

from __future__ import annotations
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Iterable


CSV_COLUMNS = [
    "lead_id",
    "company_name",
    "domain",
    "url",
    "email",
    "contact_name",
    "phone",
    "address",
    "city",
    "country",
    "niche",
    "source",
    "intent_score",
    "score_breakdown",
    "scraped_at",
    "kvk_number",
    "kbo_number",
    "btw_number",
    "has_contact",
    "has_about",
    "has_portfolio",
    "has_https",
    "title",
    "snippet",
    "query",
]


def make_lead_id(idx: int, prefix: str = "lr") -> str:
    return f"{prefix}_{idx:05d}"


def normalize_lead(lead: dict, idx: int = 0, niche: str = "") -> dict:
    """Vlak een lead dict af zodat alle CSV_COLUMNS gevuld zijn."""
    lead_id = lead.get("lead_id") or make_lead_id(idx)
    out = {col: "" for col in CSV_COLUMNS}
    for col in CSV_COLUMNS:
        val = lead.get(col)
        if val is None:
            continue
        if isinstance(val, (dict, list)):
            out[col] = json.dumps(val, ensure_ascii=False, sort_keys=True)
        else:
            out[col] = str(val)
    out["lead_id"] = lead_id
    if niche and not out.get("niche"):
        out["niche"] = niche
    return out


def export_leads(
    leads: Iterable[dict],
    niche: str = "warmtepomp",
    location: str = "all",
    fmt: str = "csv",
    directory: str | Path = "data",
) -> list[Path]:
    """Schrijf leads naar bestand(en). Returns lijst van paths."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    base = f"leads_{niche}_{location}_{today}"

    leads_list = [normalize_lead(lead, idx=i, niche=niche) for i, lead in enumerate(leads, 1)]

    paths: list[Path] = []

    if fmt in ("csv", "both"):
        csv_path = directory / f"{base}.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for lead in leads_list:
                writer.writerow(lead)
        paths.append(csv_path)
        print(f"[export] CSV: {csv_path} ({len(leads_list)} leads)")

    if fmt in ("json", "both"):
        json_path = directory / f"{base}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(leads_list, f, ensure_ascii=False, indent=2)
        paths.append(json_path)
        print(f"[export] JSON: {json_path} ({len(leads_list)} leads)")

    return paths


def append_to_master(leads: Iterable[dict], master_path: str | Path = "data/leads_master.csv") -> Path:
    """Voeg leads toe aan een master CSV (cumulatief over alle scrapes)."""
    master_path = Path(master_path)
    master_path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = master_path.exists()
    with open(master_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer.writeheader()
        for i, lead in enumerate(leads, 1):
            writer.writerow(normalize_lead(lead, idx=i))

    print(f"[export] appended to master: {master_path}")
    return master_path


if __name__ == "__main__":
    test = [{
        "company_name": "Test BV",
        "domain": "test.nl",
        "email": "info@test.nl",
        "intent_score": 65,
        "scraped_at": datetime.now().isoformat(timespec="seconds"),
    }]
    export_leads(test, niche="warmtepomp", location="amsterdam", fmt="both", directory="/tmp/lead-radar-test")
