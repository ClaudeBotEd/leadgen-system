#!/usr/bin/env python3
"""CRM-Light — CSV-based lead pipeline beheer.

Geen externe dependencies (alleen Python stdlib).

Commands:
    crm.py import <csv-of-json>           voeg leads toe (deduped op lead_id/email/domain)
    crm.py list [--stage X] [--limit N]   toon leads
    crm.py show <lead_id>                 toon een lead in detail
    crm.py update <lead_id> --stage X     update stage / velden
    crm.py note <lead_id> "text"          voeg notitie toe
    crm.py log <lead_id> --type X --content "..."  log activity
    crm.py move <lead_id> <stage>         shortcut voor stage update
    crm.py export <output.csv>            exporteer naar CSV
    crm.py stats                          pipeline statistieken
    crm.py search <query>                 full-text search

Pipeline stages:
    new -> contacted -> replied -> meeting_booked -> qualified -> negotiating -> won/lost
"""

from __future__ import annotations
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
LEADS_CSV = DATA_DIR / "leads.csv"
ACTIVITIES_CSV = DATA_DIR / "activities.csv"


LEAD_COLUMNS = [
    "lead_id", "company_name", "domain", "url", "email", "contact_name",
    "phone", "address", "city", "country", "niche", "source",
    "intent_score", "score_breakdown", "scraped_at",
    "stage", "last_contacted_at", "next_action_at",
    "owner", "notes", "custom_tags",
]

ACTIVITY_COLUMNS = [
    "activity_id", "lead_id", "type", "timestamp", "content", "outcome",
]

STAGES = [
    "new", "contacted", "replied", "meeting_booked",
    "qualified", "negotiating", "won", "lost",
]

ACTIVITY_TYPES = [
    "email_sent", "email_received", "call", "note", "stage_change",
    "linkedin_msg", "meeting", "demo",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LEADS_CSV.exists():
        with open(LEADS_CSV, "w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=LEAD_COLUMNS).writeheader()
    if not ACTIVITIES_CSV.exists():
        with open(ACTIVITIES_CSV, "w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=ACTIVITY_COLUMNS).writeheader()


def load_leads() -> list[dict]:
    ensure_data_files()
    with open(LEADS_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_leads(leads: list[dict]) -> None:
    ensure_data_files()
    with open(LEADS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEAD_COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for lead in leads:
            row = {col: "" for col in LEAD_COLUMNS}
            for k, v in lead.items():
                if k in row:
                    row[k] = "" if v is None else str(v)
            writer.writerow(row)


def load_activities() -> list[dict]:
    ensure_data_files()
    with open(ACTIVITIES_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_activity(activity: dict) -> None:
    ensure_data_files()
    with open(ACTIVITIES_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ACTIVITY_COLUMNS, quoting=csv.QUOTE_MINIMAL)
        row = {col: "" for col in ACTIVITY_COLUMNS}
        for k, v in activity.items():
            if k in row:
                row[k] = "" if v is None else str(v)
        writer.writerow(row)


def cmd_import(input_path: Path, default_stage: str = "new") -> None:
    """Importeer leads uit CSV of JSON. Dedup op lead_id/email/domain."""
    if not input_path.exists():
        print(f"[!] Bestand niet gevonden: {input_path}")
        sys.exit(2)

    new_leads: list[dict] = []
    if input_path.suffix.lower() == ".json":
        with open(input_path, "r", encoding="utf-8") as f:
            new_leads = json.load(f)
    else:
        with open(input_path, "r", encoding="utf-8") as f:
            new_leads = list(csv.DictReader(f))

    if not new_leads:
        print("[!] Geen leads in input bestand")
        return

    existing = load_leads()
    existing_ids = {l.get("lead_id", "") for l in existing if l.get("lead_id")}
    existing_emails = {l.get("email", "").lower() for l in existing if l.get("email")}
    existing_domains = {l.get("domain", "").lower() for l in existing if l.get("domain")}

    added = 0
    skipped = 0
    next_idx = len(existing) + 1

    for lead in new_leads:
        lid = (lead.get("lead_id") or "").strip()
        email = (lead.get("email") or "").lower().strip()
        domain = (lead.get("domain") or "").lower().strip()

        if lid and lid in existing_ids:
            skipped += 1
            continue
        if email and email in existing_emails:
            skipped += 1
            continue
        if domain and domain in existing_domains:
            skipped += 1
            continue

        if not lid:
            lid = f"lr_{next_idx:05d}"
            next_idx += 1
            lead["lead_id"] = lid

        if not lead.get("stage"):
            lead["stage"] = default_stage

        existing.append(lead)
        existing_ids.add(lid)
        if email:
            existing_emails.add(email)
        if domain:
            existing_domains.add(domain)
        added += 1

    save_leads(existing)
    print(f"[crm] Import: +{added} new, {skipped} duplicates skipped")
    print(f"[crm] Totaal in pipeline: {len(existing)}")


def cmd_list(stage: str | None = None, limit: int = 50, sort_by: str = "intent_score") -> None:
    leads = load_leads()
    if stage:
        leads = [l for l in leads if l.get("stage", "") == stage]

    def sort_key(l):
        v = l.get(sort_by, "")
        try:
            return -int(v)
        except (ValueError, TypeError):
            return 0
    leads.sort(key=sort_key)

    leads = leads[:limit]
    if not leads:
        print(f"[crm] Geen leads (stage={stage or 'any'})")
        return

    fmt = "{:<15} {:<3} {:<14} {:<35} {:<35}"
    print(fmt.format("ID", "S", "STAGE", "COMPANY", "EMAIL"))
    print("-" * 105)
    for l in leads:
        print(fmt.format(
            l.get("lead_id", "")[:15],
            (l.get("intent_score", "") or "")[:3],
            (l.get("stage", "") or "")[:14],
            (l.get("company_name", "") or "")[:34],
            (l.get("email", "") or "-")[:34],
        ))


def cmd_show(lead_id: str) -> None:
    leads = load_leads()
    found = next((l for l in leads if l.get("lead_id") == lead_id), None)
    if not found:
        print(f"[!] Lead niet gevonden: {lead_id}")
        sys.exit(2)

    print(f"\n=== {lead_id} ===")
    for col in LEAD_COLUMNS:
        v = found.get(col, "")
        if v:
            print(f"  {col:<20} {v}")

    activities = [a for a in load_activities() if a.get("lead_id") == lead_id]
    if activities:
        print(f"\n--- Activities ({len(activities)}) ---")
        for a in sorted(activities, key=lambda x: x.get("timestamp", "")):
            print(f"  [{a.get('timestamp','')[:19]}] {a.get('type','?'):<15} {a.get('content','')[:80]}")


def cmd_update(lead_id: str, fields: dict) -> None:
    leads = load_leads()
    found_idx = -1
    for i, l in enumerate(leads):
        if l.get("lead_id") == lead_id:
            found_idx = i
            break
    if found_idx < 0:
        print(f"[!] Lead niet gevonden: {lead_id}")
        sys.exit(2)

    old = dict(leads[found_idx])
    for k, v in fields.items():
        if v is None:
            continue
        leads[found_idx][k] = v

    if "stage" in fields and fields["stage"] != old.get("stage", ""):
        append_activity({
            "activity_id": f"act_{int(datetime.now().timestamp())}",
            "lead_id": lead_id,
            "type": "stage_change",
            "timestamp": now_iso(),
            "content": f"{old.get('stage','?')} -> {fields['stage']}",
            "outcome": "",
        })
        leads[found_idx]["last_contacted_at"] = now_iso()

    save_leads(leads)
    print(f"[crm] Updated {lead_id}: {fields}")


def cmd_note(lead_id: str, text: str) -> None:
    leads = load_leads()
    found = next((l for l in leads if l.get("lead_id") == lead_id), None)
    if not found:
        print(f"[!] Lead niet gevonden: {lead_id}")
        sys.exit(2)

    append_activity({
        "activity_id": f"act_{int(datetime.now().timestamp())}",
        "lead_id": lead_id,
        "type": "note",
        "timestamp": now_iso(),
        "content": text,
        "outcome": "",
    })

    existing_notes = found.get("notes", "")
    new_note = f"[{now_iso()[:10]}] {text}"
    found["notes"] = (existing_notes + " | " + new_note) if existing_notes else new_note
    cmd_update(lead_id, {"notes": found["notes"]})
    print(f"[crm] Note toegevoegd aan {lead_id}")


def cmd_log(lead_id: str, type_: str, content: str, outcome: str = "") -> None:
    if type_ not in ACTIVITY_TYPES:
        print(f"[!] Onbekend type. Geldig: {ACTIVITY_TYPES}")
        sys.exit(2)
    append_activity({
        "activity_id": f"act_{int(datetime.now().timestamp())}",
        "lead_id": lead_id,
        "type": type_,
        "timestamp": now_iso(),
        "content": content,
        "outcome": outcome,
    })
    if type_ in ("email_sent", "call", "linkedin_msg"):
        cmd_update(lead_id, {"last_contacted_at": now_iso()})
    print(f"[crm] Activity logged for {lead_id}: {type_}")


def cmd_export(output_path: Path) -> None:
    leads = load_leads()
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEAD_COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for l in leads:
            writer.writerow({col: l.get(col, "") for col in LEAD_COLUMNS})
    print(f"[crm] Exported {len(leads)} leads -> {output_path}")


def cmd_stats() -> None:
    leads = load_leads()
    activities = load_activities()
    if not leads:
        print("[crm] Lege pipeline. Run `crm.py import <csv>` eerst.")
        return

    by_stage: dict[str, int] = {s: 0 for s in STAGES}
    for l in leads:
        s = l.get("stage", "new")
        by_stage[s] = by_stage.get(s, 0) + 1

    print(f"\n=== Pipeline Stats ===")
    print(f"Totaal leads:      {len(leads)}")
    print(f"Totaal activities: {len(activities)}")
    print()
    for stage in STAGES:
        count = by_stage.get(stage, 0)
        bar = "#" * min(50, count) if count > 0 else ""
        print(f"  {stage:<18} {count:>4}  {bar}")

    by_niche: dict[str, int] = {}
    for l in leads:
        n = l.get("niche", "unknown")
        by_niche[n] = by_niche.get(n, 0) + 1
    if by_niche:
        print(f"\nPer niche:")
        for n, c in sorted(by_niche.items(), key=lambda x: -x[1]):
            print(f"  {n:<18} {c:>4}")

    by_country: dict[str, int] = {}
    for l in leads:
        c = l.get("country", "?")
        by_country[c] = by_country.get(c, 0) + 1
    if by_country:
        print(f"\nPer land:")
        for c, n in sorted(by_country.items(), key=lambda x: -x[1]):
            print(f"  {c:<18} {n:>4}")


def cmd_search(query: str) -> None:
    leads = load_leads()
    q = query.lower()
    matches = []
    for l in leads:
        haystack = " ".join(str(v) for v in l.values()).lower()
        if q in haystack:
            matches.append(l)

    if not matches:
        print(f"[crm] Geen matches voor '{query}'")
        return

    print(f"\n=== Matches voor '{query}' ({len(matches)}) ===")
    fmt = "{:<15} {:<3} {:<14} {:<30} {:<30}"
    for l in matches[:30]:
        print(fmt.format(
            l.get("lead_id", "")[:15],
            (l.get("intent_score", "") or "")[:3],
            (l.get("stage", "") or "")[:14],
            (l.get("company_name", "") or "")[:29],
            (l.get("email", "") or "-")[:29],
        ))


def cmd_move(lead_id: str, stage: str) -> None:
    if stage not in STAGES:
        print(f"[!] Onbekende stage. Geldig: {STAGES}")
        sys.exit(2)
    cmd_update(lead_id, {"stage": stage})


def main() -> int:
    p = argparse.ArgumentParser(description="CRM-Light - CSV-based lead pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_import = sub.add_parser("import", help="Importeer leads uit CSV/JSON")
    p_import.add_argument("file", type=Path)
    p_import.add_argument("--stage", default="new", choices=STAGES)

    p_list = sub.add_parser("list", help="Toon leads")
    p_list.add_argument("--stage", default=None)
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--sort", default="intent_score")

    p_show = sub.add_parser("show", help="Toon een lead in detail")
    p_show.add_argument("lead_id")

    p_update = sub.add_parser("update", help="Update lead velden")
    p_update.add_argument("lead_id")
    p_update.add_argument("--stage", choices=STAGES)
    p_update.add_argument("--owner")
    p_update.add_argument("--next-action-at")
    p_update.add_argument("--notes")
    p_update.add_argument("--tags", dest="custom_tags")

    p_note = sub.add_parser("note", help="Voeg notitie toe")
    p_note.add_argument("lead_id")
    p_note.add_argument("text")

    p_log = sub.add_parser("log", help="Log activity")
    p_log.add_argument("lead_id")
    p_log.add_argument("--type", required=True, choices=ACTIVITY_TYPES)
    p_log.add_argument("--content", required=True)
    p_log.add_argument("--outcome", default="")

    p_move = sub.add_parser("move", help="Shortcut: stage update")
    p_move.add_argument("lead_id")
    p_move.add_argument("stage", choices=STAGES)

    p_export = sub.add_parser("export", help="Exporteer naar CSV")
    p_export.add_argument("output", type=Path)

    sub.add_parser("stats", help="Pipeline statistieken")

    p_search = sub.add_parser("search", help="Full-text search")
    p_search.add_argument("query")

    args = p.parse_args()

    if args.cmd == "import":
        cmd_import(args.file, default_stage=args.stage)
    elif args.cmd == "list":
        cmd_list(stage=args.stage, limit=args.limit, sort_by=args.sort)
    elif args.cmd == "show":
        cmd_show(args.lead_id)
    elif args.cmd == "update":
        fields = {}
        for k in ("stage", "owner", "next_action_at", "notes", "custom_tags"):
            v = getattr(args, k.replace("-", "_"), None)
            if v is not None:
                fields[k] = v
        if not fields:
            print("[!] Geef tenminste een veld om te updaten")
            return 2
        cmd_update(args.lead_id, fields)
    elif args.cmd == "note":
        cmd_note(args.lead_id, args.text)
    elif args.cmd == "log":
        cmd_log(args.lead_id, args.type, args.content, args.outcome)
    elif args.cmd == "move":
        cmd_move(args.lead_id, args.stage)
    elif args.cmd == "export":
        cmd_export(args.output)
    elif args.cmd == "stats":
        cmd_stats()
    elif args.cmd == "search":
        cmd_search(args.query)

    return 0


if __name__ == "__main__":
    sys.exit(main())
