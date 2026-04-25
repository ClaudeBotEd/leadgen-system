#!/usr/bin/env python3
"""Outreach Personalisatie Engine.

Leest een leads CSV + een template, produceert een tekstbestand met klaar-om-te-versturen
berichten. Geen automatische verzending — output is plain text dat je in je eigen mail-tool
kopieert.

Template syntax:
    {{company_name}}    company name uit CSV
    {{first_name}}      voornaam uit contact_name (split on space)
    {{city}}            stad
    {{niche}}           warmtepomp / airco / etc.
    {{your_name}}       jouw naam (uit --signature)

Special:
    SUBJECT: <subject line>          eerste regel definieert subject
    {{rand:foo|bar|baz}}             random keuze uit opties
    {{ifempty:field|fallback}}       fallback als field leeg is

Usage:
    python personalize.py \
        --leads ../crm-light/data/leads.csv \
        --template templates/email/warmtepomp_v1.txt \
        --output outbox/batch_20260425.txt \
        --signature "Je naam" \
        --filter-stage new \
        --max 25
"""

from __future__ import annotations
import argparse
import csv
import random
import re
import sys
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent

PLACEHOLDER_RE = re.compile(r"\{\{(.*?)\}\}")
RAND_RE = re.compile(r"^rand:(.+)$")
IFEMPTY_RE = re.compile(r"^ifempty:([^|]+)\|(.+)$")


def load_template(template_path: Path) -> tuple[str, str]:
    """Load template, return (subject_line, body)."""
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    subject = ""
    body_start = 0

    if lines and lines[0].upper().startswith("SUBJECT:"):
        subject = lines[0][len("SUBJECT:"):].strip()
        body_start = 1
        if len(lines) > 1 and not lines[1].strip():
            body_start = 2

    body = "\n".join(lines[body_start:])
    return subject, body.strip()


def render_field(field: str, lead: dict, extra: dict | None = None) -> str:
    extra = extra or {}
    field = field.strip()

    rand_match = RAND_RE.match(field)
    if rand_match:
        options = [o.strip() for o in rand_match.group(1).split("|")]
        return random.choice(options)

    ifempty_match = IFEMPTY_RE.match(field)
    if ifempty_match:
        key = ifempty_match.group(1).strip()
        fallback = ifempty_match.group(2).strip()
        val = lead.get(key) or extra.get(key)
        return val if val else fallback

    if field in extra:
        return str(extra[field])

    if field == "first_name":
        contact = lead.get("contact_name", "")
        if contact:
            return contact.split()[0]
        return "daar"

    if field == "domain_short":
        domain = lead.get("domain", "")
        return domain.split(".")[0] if domain else ""

    if field == "today":
        return datetime.now().strftime("%d-%m-%Y")

    return str(lead.get(field, ""))


def render_template(template: str, lead: dict, extra: dict | None = None) -> str:
    def replacer(m):
        return render_field(m.group(1), lead, extra)
    return PLACEHOLDER_RE.sub(replacer, template)


def filter_leads(
    leads: list[dict],
    stage: str | None = None,
    min_score: int = 0,
    has_email: bool = True,
    niche: str | None = None,
    country: str | None = None,
    max_count: int | None = None,
    skip_lead_ids: set[str] | None = None,
) -> list[dict]:
    out = []
    skip = skip_lead_ids or set()
    for l in leads:
        if has_email and not l.get("email"):
            continue
        if l.get("lead_id") in skip:
            continue
        if stage and l.get("stage") != stage:
            continue
        if niche and l.get("niche") != niche:
            continue
        if country and l.get("country", "").upper() != country.upper():
            continue
        try:
            score = int(l.get("intent_score", "0") or "0")
        except (TypeError, ValueError):
            score = 0
        if score < min_score:
            continue
        out.append(l)
    if max_count:
        out = out[:max_count]
    return out


def render_batch(
    leads: list[dict],
    subject_tpl: str,
    body_tpl: str,
    extra: dict | None = None,
) -> list[dict]:
    out = []
    for lead in leads:
        subj = render_template(subject_tpl, lead, extra) if subject_tpl else ""
        body = render_template(body_tpl, lead, extra)
        out.append({
            "lead_id": lead.get("lead_id", ""),
            "to": lead.get("email", ""),
            "company": lead.get("company_name", ""),
            "subject": subj,
            "body": body,
        })
    return out


def write_outbox(messages: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Outreach batch - {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"# {len(messages)} berichten\n")
        f.write("# Kopieer elk bericht naar je eigen mail tool en verstuur handmatig.\n")
        f.write("# Markeer in CRM via: python crm.py log <lead_id> --type email_sent --content '...'\n\n")
        for i, msg in enumerate(messages, 1):
            f.write("=" * 80 + "\n")
            f.write(f"# {i}. {msg['lead_id']} - {msg['company']}\n")
            f.write(f"To:      {msg['to']}\n")
            f.write(f"Subject: {msg['subject']}\n")
            f.write("-" * 80 + "\n")
            f.write(msg["body"].strip() + "\n\n")


def write_outbox_eml(messages: list[dict], output_dir: Path) -> None:
    """Schrijf elke message als losse .eml file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, msg in enumerate(messages, 1):
        safe_id = re.sub(r"[^a-zA-Z0-9_]", "_", msg["lead_id"] or f"msg_{i}")
        eml = (
            f"To: {msg['to']}\n"
            f"Subject: {msg['subject']}\n"
            f"Content-Type: text/plain; charset=UTF-8\n"
            f"\n"
            f"{msg['body']}\n"
        )
        with open(output_dir / f"{safe_id}.eml", "w", encoding="utf-8") as f:
            f.write(eml)


def main() -> int:
    p = argparse.ArgumentParser(description="Outreach personalisatie engine")
    p.add_argument("--leads", required=True, type=Path, help="Pad naar leads CSV")
    p.add_argument("--template", required=True, type=Path, help="Pad naar template .txt")
    p.add_argument("--output", default=None, type=Path, help="Output bestand (default: outbox/batch_<date>.txt)")
    p.add_argument("--signature", default="Je naam", help="Vervangt {{your_name}}")
    p.add_argument("--from-email", default="", help="Vervangt {{your_email}}")
    p.add_argument("--from-company", default="", help="Vervangt {{your_company}}")

    p.add_argument("--filter-stage", default=None)
    p.add_argument("--filter-niche", default=None)
    p.add_argument("--filter-country", default=None, choices=["NL", "BE", "nl", "be"])
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--max", type=int, default=None)

    p.add_argument("--skip-already-contacted", action="store_true")
    p.add_argument("--eml", action="store_true", help="Schrijf .eml bestanden")

    args = p.parse_args()

    if not args.leads.exists():
        print(f"[!] Leads CSV niet gevonden: {args.leads}")
        return 2
    if not args.template.exists():
        print(f"[!] Template niet gevonden: {args.template}")
        return 2

    with open(args.leads, "r", encoding="utf-8") as f:
        leads = list(csv.DictReader(f))

    skip_ids: set[str] = set()
    if args.skip_already_contacted:
        skip_ids = {l.get("lead_id", "") for l in leads if l.get("last_contacted_at")}

    filtered = filter_leads(
        leads,
        stage=args.filter_stage,
        min_score=args.min_score,
        niche=args.filter_niche,
        country=args.filter_country,
        max_count=args.max,
        skip_lead_ids=skip_ids,
    )
    print(f"[outreach] {len(filtered)} leads na filtering (uit {len(leads)})")

    if not filtered:
        print("[!] Geen leads om te targeten")
        return 1

    subject_tpl, body_tpl = load_template(args.template)
    extra = {
        "your_name": args.signature,
        "your_email": args.from_email,
        "your_company": args.from_company,
    }
    messages = render_batch(filtered, subject_tpl, body_tpl, extra=extra)

    output = args.output or (HERE / "outbox" / f"batch_{datetime.now().strftime('%Y%m%d')}.txt")

    if args.eml:
        out_dir = output if output.suffix == "" else output.with_suffix("")
        write_outbox_eml(messages, out_dir)
        print(f"[outreach] {len(messages)} .eml bestanden -> {out_dir}/")
    else:
        write_outbox(messages, output)
        print(f"[outreach] {len(messages)} berichten -> {output}")

    print(f"\nNu:")
    print(f"  1. Open {output}")
    print(f"  2. Kopieer elk bericht naar je mail tool")
    print(f"  3. Verstuur (max 30/dag/mailbox voor warmup)")
    print(f"  4. Log in CRM: python ../crm-light/crm.py log <lead_id> --type email_sent --content '...'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
