#!/usr/bin/env python3
"""Consumer Lead Radar — CLI.

Daily mode (1 command, alles gepusht naar Sheets):
    python run_consumer.py --daily

Single niche:
    python run_consumer.py --niche warmtepomp --location nederland --limit 50
    python run_consumer.py --niche airco --sources reddit,tweakers --limit 100
    python run_consumer.py --niche warmtepomp --facebook-file fb_posts.txt

Geen Reddit-API key nodig.  Geen automatische outreach — discovery,
filtering, scoring, CSV/JSON output, optioneel Google Sheets sync.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from consumer import Lead, RawPost, intent_from_score  # noqa: E402
from consumer.sources import REGISTRY, ALL_SOURCES, analyze_manual_posts  # noqa: E402
from consumer.sources.facebook import load_posts_from_file  # noqa: E402
from consumer.processor import clean_post, is_potential_lead, score_post  # noqa: E402
from consumer.output import export_leads, sync_to_sheets  # noqa: E402
from consumer.utils import PoliteSession, HttpConfig, SeenStore  # noqa: E402

log = logging.getLogger("consumer.cli")

DEFAULT_QUERIES_YAML = HERE / "consumer" / "queries.yaml"
DEFAULT_OUTDIR = HERE / "data" / "leads" / "consumer"

# Defaults voor --daily mode (production usage)
DAILY_NICHES = ["warmtepomp", "airco", "zonnepanelen", "cv", "renovatie"]
DAILY_LOCATION = "nederland"
DAILY_LIMIT = 25
DAILY_MAX_QUERIES = 5
DAILY_MIN_SCORE = 70   # alleen HOT/WARM richting sheets
DAILY_MAX_AGE_DAYS = 7


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(path: Path) -> dict:
    if not path.exists():
        log.warning("queries.yaml niet gevonden: %s — gebruik defaults", path)
        return {"defaults": {}, "niches": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Consumer lead radar — vindt high-intent NL/BE leads")

    # Daily preset (alle niches in 1 command)
    p.add_argument("--daily", action="store_true",
                   help="Daily preset: alle niches, score>=70, time filter 7d, sheets sync. Geen --niche nodig.")

    # Niche-specifiek (of via --daily over alle niches)
    p.add_argument("--niche", default=None,
                   help="Niche (warmtepomp/airco/zonnepanelen/cv/renovatie). Vereist tenzij --daily.")
    p.add_argument("--location", default=None,
                   help="Locatie (bv 'nederland', 'amsterdam'). Optioneel.")
    p.add_argument("--limit", type=int, default=50,
                   help="Max raw posts per source-query (default 50)")
    p.add_argument("--sources", default="",
                   help=f"Komma-lijst sources. Default = alles. Beschikbaar: {','.join(ALL_SOURCES)}")
    p.add_argument("--min-score", type=int, default=30,
                   help="Minimum score om in output op te nemen (default 30; --daily dwingt 70)")
    p.add_argument("--max-age-days", type=int, default=0,
                   help="Filter posts ouder dan N dagen weg (0 = uit; --daily dwingt 7)")
    p.add_argument("--queries-file", default=str(DEFAULT_QUERIES_YAML))
    p.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    p.add_argument("--facebook-file", default=None,
                   help="Optioneel pad naar tekstbestand met handmatige FB-posts")
    p.add_argument("--no-dedup", action="store_true",
                   help="Cross-run dedup uit (negeer seen_hashes.json)")
    p.add_argument("--max-queries", type=int, default=8,
                   help="Max # tekst-queries per niche (default 8)")

    # Google Sheets
    p.add_argument("--sheets", action="store_true",
                   help="Push leads naar Google Sheets (--daily zet dit automatisch)")
    p.add_argument("--spreadsheet-id", default=None,
                   help="Spreadsheet ID. Default: env LEAD_RADAR_SPREADSHEET_ID")
    p.add_argument("--credentials", default=None,
                   help="Pad naar Google service-account JSON")

    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    if not args.daily and not args.niche:
        p.error("Geef --niche <name> of --daily")
    return args


def expand_queries(niche_cfg: dict, location: str | None, max_queries: int) -> dict[str, list[str]]:
    text_qs = (niche_cfg.get("queries_text") or [])[:max_queries]
    google_qs = (niche_cfg.get("google_queries") or [])[:max_queries]
    market_qs = (niche_cfg.get("marktplaats_queries") or [])[:max_queries]

    def loc_subst(qs: list[str]) -> list[str]:
        out = []
        for q in qs:
            if "{location}" in q:
                out.append(q.replace("{location}", location or "nederland"))
            else:
                if location:
                    out.append(f"{q} {location}")
                else:
                    out.append(q)
        return out

    return {
        "reddit": loc_subst(text_qs),
        "tweakers": text_qs,
        "bouwinfo": text_qs,
        "google": loc_subst(google_qs) if google_qs else loc_subst(text_qs),
        "marktplaats": market_qs or text_qs,
    }


def _is_recent(created_at: str | None, cutoff_utc: datetime | None) -> bool:
    """Permissief: geen timestamp = keep.  Anders ouder-dan-cutoff = drop."""
    if cutoff_utc is None or not created_at:
        return True
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt >= cutoff_utc
    except Exception:
        return True


def run_one_niche(args: argparse.Namespace, niche: str) -> list[Lead]:
    """Run pipeline voor 1 niche en returnt de Lead-list."""
    cfg = load_config(Path(args.queries_file))
    niches = cfg.get("niches") or {}
    if niche not in niches:
        log.error("Niche %r niet in queries.yaml", niche)
        return []
    niche_cfg = niches[niche]
    keywords_required = niche_cfg.get("keywords_required") or [niche]

    requested = [s.strip() for s in args.sources.split(",") if s.strip()] if args.sources else ALL_SOURCES
    invalid = [s for s in requested if s not in REGISTRY]
    if invalid:
        log.error("Onbekende sources: %s", invalid)
        return []

    queries_per_source = expand_queries(niche_cfg, args.location, args.max_queries)
    log.info("=== %s @ %s | sources=%s limit=%d min_score=%d max_age_days=%d ===",
             niche, args.location, requested, args.limit, args.min_score, args.max_age_days)

    seen = SeenStore(Path(args.outdir) / "seen_hashes.json") if not args.no_dedup else None
    if seen:
        log.info("Dedup store: %d eerder geziene posts", len(seen))

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.max_age_days)) if args.max_age_days > 0 else None

    raw_total: list[RawPost] = []
    polite = PoliteSession(HttpConfig(request_delay=2.0))

    for source_name in requested:
        fetch = REGISTRY[source_name]
        queries = queries_per_source.get(source_name) or []
        if not queries:
            continue
        for q in queries:
            t0 = time.monotonic()
            try:
                posts = fetch(q, limit=args.limit, location=None, session=polite)
            except Exception as e:
                log.warning("Source %s crashte op q=%r: %s", source_name, q, e)
                posts = []
            log.info("[%s] q=%r -> %d posts in %.1fs", source_name, q, len(posts), time.monotonic() - t0)
            for p in posts:
                if seen and seen.has(p.fingerprint()):
                    continue
                raw_total.append(p)

    in_memory_seen: set[str] = set()
    leads: list[Lead] = []
    skipped_promo = skipped_low = skipped_old = 0

    for raw in raw_total:
        fp = raw.fingerprint()
        if fp in in_memory_seen:
            continue
        in_memory_seen.add(fp)

        if not _is_recent(raw.created_at, cutoff):
            skipped_old += 1
            continue

        cleaned = clean_post(raw)
        if not is_potential_lead(cleaned["full"]):
            skipped_promo += 1
            continue
        score, breakdown = score_post(cleaned, niche_keywords=keywords_required)
        if score < args.min_score:
            skipped_low += 1
            continue
        leads.append(Lead(
            id=raw.id,
            source=raw.source,
            title=cleaned["title"] or raw.title,
            text=cleaned["text"],
            summary=cleaned["summary"],
            url=raw.url,
            city=cleaned["city"],
            score=score,
            intent=intent_from_score(score),
            breakdown=breakdown,
            niche=niche,
            author=raw.author,
            created_at=raw.created_at,
        ))
        if seen:
            seen.add(fp)

    if args.facebook_file:
        fb_posts = load_posts_from_file(args.facebook_file)
        log.info("FB handmatig: %d posts", len(fb_posts))
        leads.extend(analyze_manual_posts(
            fb_posts, niche=niche, niche_keywords=keywords_required, min_score=args.min_score,
        ))

    if seen:
        seen.save()

    log.info("[%s] raw=%d -> leads=%d (promo=%d, oud=%d, lowscore=%d)",
             niche, len(raw_total), len(leads), skipped_promo, skipped_old, skipped_low)

    export_leads(leads, niche=niche, outdir=args.outdir)
    return leads


def _print_summary(niche: str, leads: list[Lead], sheets_result: dict | None) -> None:
    hot = sum(1 for l in leads if l.score >= 80)
    warm = sum(1 for l in leads if 70 <= l.score < 80)
    print()
    print("─" * 70)
    print(f"  {niche:<14}  leads={len(leads):>3}   HOT(>=80)={hot:>3}   WARM(70-79)={warm:>3}")
    if sheets_result:
        print(f"                  sheets ALL +{sheets_result['all_added']}  HOT +{sheets_result['hot_added']}")
    if leads:
        top = sorted(leads, key=lambda l: l.score, reverse=True)[:3]
        for l in top:
            mark = "🔥" if l.score >= 80 else "⚡"
            city = (l.city or "—")[:12]
            print(f"   {mark} [{l.score:>3}] {city:<14} {l.title[:50]}")


def run_daily(args: argparse.Namespace) -> int:
    """Run alle niches, alleen score>=70, push naar Sheets."""
    args.location = args.location or DAILY_LOCATION
    args.limit = args.limit if args.limit != 50 else DAILY_LIMIT
    args.max_queries = args.max_queries if args.max_queries != 8 else DAILY_MAX_QUERIES
    args.min_score = max(args.min_score, DAILY_MIN_SCORE)
    args.max_age_days = args.max_age_days if args.max_age_days > 0 else DAILY_MAX_AGE_DAYS
    args.sheets = True

    print()
    print("=" * 70)
    print(f"  CONSUMER LEAD RADAR  —  DAILY  ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"  location={args.location}  limit={args.limit}  min_score>={args.min_score}  max_age={args.max_age_days}d")
    print("=" * 70)

    cfg = load_config(Path(args.queries_file))
    available = list((cfg.get("niches") or {}).keys())
    niches_to_run = [n for n in DAILY_NICHES if n in available]

    grand_total: list[Lead] = []
    sheets_total = {"all_added": 0, "hot_added": 0, "spreadsheet_url": ""}

    for niche in niches_to_run:
        leads = run_one_niche(args, niche)
        sheets_result = None
        if leads:
            try:
                sheets_result = sync_to_sheets(
                    leads,
                    spreadsheet_id=args.spreadsheet_id,
                    credentials_path=args.credentials,
                )
                sheets_total["all_added"] += sheets_result["all_added"]
                sheets_total["hot_added"] += sheets_result["hot_added"]
                sheets_total["spreadsheet_url"] = sheets_result["spreadsheet_url"]
            except Exception as e:
                log.error("Sheets sync (%s) faalde: %s", niche, e)
        _print_summary(niche, leads, sheets_result)
        grand_total.extend(leads)

    print()
    print("=" * 70)
    print(f"  TOTAAL: {len(grand_total)} qualified leads (score>=70)")
    if sheets_total["spreadsheet_url"]:
        print(f"  Sheets: +{sheets_total['all_added']} ALL  +{sheets_total['hot_added']} HOT")
        print(f"  Open  : {sheets_total['spreadsheet_url']}")
    print("=" * 70)
    return 0


def run_single(args: argparse.Namespace) -> int:
    leads = run_one_niche(args, args.niche)
    sheets_result = None
    if args.sheets and leads:
        try:
            sheets_result = sync_to_sheets(
                leads,
                spreadsheet_id=args.spreadsheet_id,
                credentials_path=args.credentials,
            )
        except Exception as e:
            log.error("Sheets sync faalde: %s", e)
    _print_summary(args.niche, leads, sheets_result)
    print()
    return 0


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)
    try:
        if args.daily:
            return run_daily(args)
        return run_single(args)
    except KeyboardInterrupt:
        log.warning("Onderbroken door gebruiker")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
