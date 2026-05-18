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

from pcs import ensure_leads_master_workflow, normalize_state


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
    "assigned_to",
    "sent_at",
    "state",
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
    out["state"] = normalize_state(out.get("state"))
    return out


def export_leads(
    leads: Iterable[dict],
    niche: str = "warmtepomp",
    location: str = "all",
    fmt: str = "csv",
    directory: str | Path = "data",
) -> list[Path]:
    """Schrijf leads naar bestand(en). Returns lijst van paths.

    If LEAD_RADAR_INTELLIGENCE_ENABLED=1, every exported lead is also fed
    through the llm-council AI intelligence layer (scoring -> outreach ->
    CRM persist -> optional n8n webhook). The CSV/JSON output is unchanged
    so existing downstream tools keep working.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    base = f"leads_{niche}_{location}_{today}"

    raw_list = list(leads)
    leads_list = [normalize_lead(lead, idx=i, niche=niche) for i, lead in enumerate(raw_list, 1)]
    # Stamp the assigned lead_id back onto the raw row so the moderation
    # layer (which keeps arbitrary fields like source_url / snippet that
    # CSV normalisation strips) still has a stable identifier.
    moderation_rows: list[dict] = []
    for i, (raw, normed) in enumerate(zip(raw_list, leads_list), 1):
        merged = {**raw, "lead_id": normed.get("lead_id"), "candidate_id": normed.get("lead_id")}
        moderation_rows.append(merged)

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

    _maybe_run_moderation(moderation_rows)

    return paths


def _maybe_run_moderation(leads_list: list[dict]) -> None:
    """Best-effort moderation hook. Never raises into the exporter.

    The moderation layer takes captured *public posts* (source_url +
    snippet + captured_at), not B2B company rows. Most lead-radar
    exporters today produce company rows, so we only forward rows that
    actually look like post candidates. Activated by
    LEAD_RADAR_MODERATION_ENABLED.
    """
    try:
        from moderation import get_config, moderate_posts  # lazy import
    except ImportError as e:
        print(f"[export] moderation import failed (skipping): {e}")
        return

    config = get_config()
    if not config.enabled:
        return

    candidates = [
        row for row in leads_list
        if str(row.get("source_url") or "").strip()
        and str(row.get("snippet") or "").strip()
        and str(row.get("captured_at") or "").strip()
    ]
    if not candidates:
        print(
            f"[moderation] skipped — none of the {len(leads_list)} rows are post-shaped "
            "(need source_url + snippet + captured_at). The moderation layer is "
            "intended for forum/social scrape output, not the company exporter."
        )
        return

    try:
        summary = moderate_posts(candidates, config=config)
        print(
            f"[moderation] reviewed={summary.reviewed} approved={summary.approved} "
            f"persisted={summary.persisted} webhooks={summary.webhooks_fired} "
            f"errors={summary.errors}"
        )
        if summary.temperature_counts:
            print(f"[moderation] temperatures={dict(summary.temperature_counts)}")
        if summary.error_kinds:
            print(f"[moderation] error_kinds={dict(summary.error_kinds)}")
    except Exception as e:  # noqa: BLE001 — protect the pipeline from any bug
        print(f"[moderation] crashed (continuing): {e}")


def append_to_master(leads: Iterable[dict], master_path: str | Path = "data/leads_master.csv") -> Path:
    """Voeg leads toe aan een master CSV (cumulatief over alle scrapes)."""
    master_path = Path(master_path)
    master_path.parent.mkdir(parents=True, exist_ok=True)
    ensure_leads_master_workflow(master_path, base_fields=CSV_COLUMNS)

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
