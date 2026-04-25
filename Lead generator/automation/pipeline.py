#!/usr/bin/env python3
"""End-to-end pipeline runner.

Doet in 1 commando:
    1. lead-radar  -> scrape + score + export naar CSV
    2. crm-light   -> import CSV in master leads.csv (deduped)
    3. outreach    -> genereer email batch (klaar om te verzenden)
    4. dashboard   -> toon pipeline status

Usage:
    python pipeline.py --niche warmtepomp --location amsterdam --max 50
    python pipeline.py --niche airco --location antwerpen --country be --no-outreach
"""

from __future__ import annotations
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEAD_RADAR = ROOT / "lead-radar"
CRM_LIGHT = ROOT / "crm-light"
OUTREACH = ROOT / "outreach"


def run_step(label: str, cmd: list[str], cwd: Path) -> int:
    print(f"\n{'=' * 70}")
    print(f"STEP: {label}")
    print(f"CMD:  {' '.join(cmd)}")
    print(f"CWD:  {cwd}")
    print('=' * 70)
    proc = subprocess.run(cmd, cwd=str(cwd))
    if proc.returncode != 0:
        print(f"[!] Step '{label}' faalde met exit code {proc.returncode}")
    return proc.returncode


def find_latest_csv(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def main() -> int:
    p = argparse.ArgumentParser(description="Lead-Gen End-to-End Pipeline")
    p.add_argument("--niche", required=True, choices=["warmtepomp", "airco", "zonnepanelen", "hvac_generiek"])
    p.add_argument("--location", required=True)
    p.add_argument("--country", default="nl", choices=["nl", "be"])
    p.add_argument("--max", type=int, default=25)
    p.add_argument("--min-score", type=int, default=30)
    p.add_argument("--no-scrape", action="store_true")
    p.add_argument("--no-crm", action="store_true")
    p.add_argument("--no-outreach", action="store_true")
    p.add_argument("--no-dashboard", action="store_true")
    p.add_argument("--template", default=None)
    p.add_argument("--signature", default="Je naam")
    p.add_argument("--from-email", default="")
    p.add_argument("--from-company", default="")
    p.add_argument("--outreach-max", type=int, default=20)

    args = p.parse_args()

    print(f"\n[pipeline] Start: {datetime.now().isoformat(timespec='seconds')}")
    print(f"[pipeline] Niche={args.niche}, Location={args.location}, Country={args.country}\n")

    leads_csv: Path | None = None

    # Step 1: scrape
    if not args.no_scrape:
        cmd = [
            sys.executable, "run.py",
            "--niche", args.niche,
            "--location", args.location,
            "--country", args.country,
            "--max-results", str(args.max),
            "--min-score", str(args.min_score),
            "--master",
        ]
        rc = run_step("Lead Radar (scrape)", cmd, cwd=LEAD_RADAR)
        if rc != 0:
            print("[!] Scrape faalde - check error en probeer opnieuw")
            return rc

        pattern = f"leads_{args.niche}_{args.location}_*.csv"
        leads_csv = find_latest_csv(LEAD_RADAR / "data", pattern)
        if not leads_csv:
            print(f"[!] Geen scrape output gevonden in {LEAD_RADAR / 'data'}")
            return 2
        print(f"[pipeline] scrape output: {leads_csv}")
    else:
        pattern = f"leads_{args.niche}_{args.location}_*.csv"
        leads_csv = find_latest_csv(LEAD_RADAR / "data", pattern)
        if not leads_csv:
            print(f"[!] --no-scrape gezet maar geen bestaande CSV gevonden")
            return 2
        print(f"[pipeline] gebruik bestaande CSV: {leads_csv}")

    # Step 2: CRM import
    if not args.no_crm:
        cmd = [sys.executable, "crm.py", "import", str(leads_csv)]
        run_step("CRM-Light (import)", cmd, cwd=CRM_LIGHT)

    # Step 3: outreach
    if not args.no_outreach:
        template = args.template
        if not template:
            template_candidates = [
                f"templates/email/{args.niche}_v1.txt",
                f"templates/email/hvac_generiek_v1.txt",
                f"templates/email/warmtepomp_v1.txt",
            ]
            for t in template_candidates:
                if (OUTREACH / t).exists():
                    template = t
                    break
        if not template or not (OUTREACH / template).exists():
            print(f"[!] Geen template gevonden voor niche={args.niche}, skip outreach")
        else:
            output_path = OUTREACH / "outbox" / f"batch_{args.niche}_{args.location}_{datetime.now().strftime('%Y%m%d')}.txt"
            cmd = [
                sys.executable, "personalize.py",
                "--leads", str(CRM_LIGHT / "data" / "leads.csv"),
                "--template", template,
                "--output", str(output_path),
                "--signature", args.signature,
                "--from-email", args.from_email,
                "--from-company", args.from_company,
                "--filter-stage", "new",
                "--filter-niche", args.niche,
                "--min-score", str(args.min_score),
                "--max", str(args.outreach_max),
                "--skip-already-contacted",
            ]
            run_step("Outreach (personalize)", cmd, cwd=OUTREACH)

    # Step 4: dashboard
    if not args.no_dashboard:
        run_step("CRM-Light (dashboard)", [sys.executable, "dashboard.py"], cwd=CRM_LIGHT)

    print(f"\n[pipeline] Done: {datetime.now().isoformat(timespec='seconds')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
