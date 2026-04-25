#!/usr/bin/env python3
"""CRM-Light — Terminal dashboard.

Toont overzicht: pipeline funnel, top leads, stale leads, recent activity, KPIs.
Read-only — bewerkt niets in de CSV files.

Usage:
    python dashboard.py
    python dashboard.py --refresh 30    # auto-refresh
"""

from __future__ import annotations
import argparse
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from crm import load_leads, load_activities, STAGES  # noqa: E402


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    return s[:n] if len(s) <= n else s[: n - 1] + "..."


def _human_age(iso_ts: str) -> str:
    if not iso_ts:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except Exception:
        return "-"
    now = datetime.now(timezone.utc)
    delta = now - dt
    sec = int(delta.total_seconds())
    if sec < 60:
        return f"{sec}s ago"
    if sec < 3600:
        return f"{sec // 60}m ago"
    if sec < 86400:
        return f"{sec // 3600}h ago"
    return f"{sec // 86400}d ago"


def render_dashboard() -> None:
    leads = load_leads()
    activities = load_activities()

    print("=" * 80)
    print("  CRM-LIGHT DASHBOARD".center(80))
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}".center(80))
    print("=" * 80)

    if not leads:
        print("\n  Lege pipeline. Run 'python crm.py import <csv>' om te starten.\n")
        return

    print("\n  Pipeline funnel:")
    by_stage: dict[str, int] = {s: 0 for s in STAGES}
    for l in leads:
        s = l.get("stage", "new")
        by_stage[s] = by_stage.get(s, 0) + 1

    max_count = max(by_stage.values()) if by_stage else 1
    bar_width = 40
    for stage in STAGES:
        count = by_stage.get(stage, 0)
        bar_len = int((count / max_count) * bar_width) if max_count else 0
        bar = "#" * bar_len
        print(f"    {stage:<18} {count:>4}  {bar}")

    print("\n  Top 10 leads (by intent_score):")
    sorted_leads = sorted(
        leads,
        key=lambda l: int(l.get("intent_score", "0") or "0"),
        reverse=True,
    )
    print(f"    {'ID':<14} {'S':>3} {'STAGE':<14} {'COMPANY':<28} {'EMAIL':<28}")
    print("    " + "-" * 92)
    for l in sorted_leads[:10]:
        print(f"    {_truncate(l.get('lead_id', ''), 14):<14} "
              f"{(l.get('intent_score', '') or '-'):>3} "
              f"{_truncate(l.get('stage', ''), 14):<14} "
              f"{_truncate(l.get('company_name', ''), 28):<28} "
              f"{_truncate(l.get('email', '') or '-', 28):<28}")

    print("\n  Stale leads (>3 days no contact, actief):")
    active_stages = {"contacted", "replied", "meeting_booked", "qualified", "negotiating"}
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    stale = []
    for l in leads:
        if l.get("stage", "") not in active_stages:
            continue
        last = l.get("last_contacted_at", "")
        if not last:
            continue
        try:
            dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if dt < cutoff:
                stale.append((l, dt))
        except Exception:
            continue

    stale.sort(key=lambda x: x[1])
    if stale:
        for lead, _ in stale[:8]:
            print(f"    {lead.get('lead_id',''):<14} "
                  f"{lead.get('stage', ''):<14} "
                  f"{_truncate(lead.get('company_name', ''), 30):<30}  "
                  f"last: {_human_age(lead.get('last_contacted_at', ''))}")
    else:
        print("    (geen stale leads)")

    print("\n  Recente activities:")
    sorted_activities = sorted(activities, key=lambda a: a.get("timestamp", ""), reverse=True)
    if sorted_activities:
        for a in sorted_activities[:10]:
            print(f"    [{a.get('timestamp','')[:16]}] "
                  f"{a.get('lead_id','-'):<14} "
                  f"{a.get('type','?'):<15} "
                  f"{_truncate(a.get('content',''), 40):<40}")
    else:
        print("    (geen activities yet)")

    print("\n  KPIs:")
    won = sum(1 for l in leads if l.get("stage") == "won")
    contacted = sum(1 for l in leads if l.get("stage") in {"contacted", "replied", "meeting_booked", "qualified", "negotiating", "won", "lost"})
    replied = sum(1 for l in leads if l.get("stage") in {"replied", "meeting_booked", "qualified", "negotiating", "won", "lost"})
    booked = sum(1 for l in leads if l.get("stage") in {"meeting_booked", "qualified", "negotiating", "won", "lost"})

    contact_rate = (contacted / len(leads) * 100) if leads else 0
    reply_rate = (replied / contacted * 100) if contacted else 0
    book_rate = (booked / replied * 100) if replied else 0
    win_rate = (won / booked * 100) if booked else 0

    print(f"    Leads totaal:       {len(leads)}")
    print(f"    % gecontacteerd:    {contact_rate:5.1f}%   ({contacted}/{len(leads)})")
    print(f"    Reply rate:         {reply_rate:5.1f}%   ({replied}/{contacted})")
    print(f"    Meeting book rate:  {book_rate:5.1f}%   ({booked}/{replied})")
    print(f"    Win rate (booked):  {win_rate:5.1f}%   ({won}/{booked})")

    print("\n" + "=" * 80)


def main() -> int:
    p = argparse.ArgumentParser(description="CRM-Light Dashboard")
    p.add_argument("--refresh", type=int, default=0, help="Auto-refresh interval in seconden")
    args = p.parse_args()

    if args.refresh > 0:
        try:
            while True:
                clear_screen()
                render_dashboard()
                print(f"\n  (refresh in {args.refresh}s - Ctrl+C om te stoppen)")
                time.sleep(args.refresh)
        except KeyboardInterrupt:
            return 0
    else:
        render_dashboard()
    return 0


if __name__ == "__main__":
    sys.exit(main())
