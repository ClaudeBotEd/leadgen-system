#!/usr/bin/env python3
"""Consumer Lead Radar — CLI.

Voorbeelden:
    python run_consumer.py --niche warmtepomp --location nederland --limit 50
    python run_consumer.py --niche airco --sources reddit,tweakers --limit 100
    python run_consumer.py --niche cv --location amsterdam --min-score 50 --verbose
    python run_consumer.py --niche warmtepomp --facebook-file fb_posts.txt

Geen Reddit-API key nodig.  Geen automatische outreach — alleen discovery,
filtering, scoring, en CSV/JSON output.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from consumer import Lead, RawPost, intent_from_score  # noqa: E402
from consumer.sources import REGISTRY, ALL_SOURCES, analyze_manual_posts  # noqa: E402
from consumer.sources.facebook import load_posts_from_file  # noqa: E402
from consumer.processor import clean_post, is_potential_lead, score_post  # noqa: E402
from consumer.output import export_leads  # noqa: E402
from consumer.utils import PoliteSession, HttpConfig, SeenStore  # noqa: E402

log = logging.getLogger("consumer.cli")

DEFAULT_QUERIES_YAML = HERE / "consumer" / "queries.yaml"
DEFAULT_OUTDIR = HERE / "data" / "leads" / "consumer"


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
    p.add_argument("--niche", required=True,
                   help="Niche (warmtepomp, airco, zonnepanelen, cv, renovatie). Moet bestaan in queries.yaml")
    p.add_argument("--location", default=None,
                   help="Locatie (bv 'nederland', 'amsterdam', 'antwerpen'). Optioneel.")
    p.add_argument("--limit", type=int, default=50,
                   help="Max raw posts per source-query (default 50)")
    p.add_argument("--sources", default="",
                   help=f"Komma-lijst sources. Default = alle scrapers. Beschikbaar: {','.join(ALL_SOURCES)}")
    p.add_argument("--min-score", type=int, default=30,
                   help="Minimum score om in output op te nemen (default 30)")
    p.add_argument("--queries-file", default=str(DEFAULT_QUERIES_YAML),
                   help="Pad naar queries.yaml")
    p.add_argument("--outdir", default=str(DEFAULT_OUTDIR),
                   help="Output dir (default lead-radar/data/leads/consumer/)")
    p.add_argument("--facebook-file", default=None,
                   help="Optioneel pad naar tekstbestand met handmatige FB-posts (gescheiden door blanke regel of '---')")
    p.add_argument("--no-dedup", action="store_true",
                   help="Cross-run dedup uitzetten (gebruik niet seen_hashes.json)")
    p.add_argument("--max-queries", type=int, default=8,
                   help="Max # tekst-queries per niche (default 8) — beschermt tegen lange runs")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def expand_queries(niche_cfg: dict, location: str | None, max_queries: int) -> dict[str, list[str]]:
    """Bouw per source een lijst zoekqueries op basis van queries.yaml + location."""
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


def run_pipeline(args: argparse.Namespace) -> int:
    cfg = load_config(Path(args.queries_file))
    niches = cfg.get("niches") or {}
    if args.niche not in niches:
        log.error("Niche %r niet gevonden in %s. Beschikbaar: %s",
                  args.niche, args.queries_file, ", ".join(niches.keys()) or "<geen>")
        return 2
    niche_cfg = niches[args.niche]
    keywords_required = niche_cfg.get("keywords_required") or [args.niche]

    requested = [s.strip() for s in args.sources.split(",") if s.strip()] if args.sources else ALL_SOURCES
    invalid = [s for s in requested if s not in REGISTRY]
    if invalid:
        log.error("Onbekende source(s): %s. Geldig: %s", invalid, list(REGISTRY))
        return 2

    queries_per_source = expand_queries(niche_cfg, args.location, args.max_queries)
    log.info("Niche=%s location=%s sources=%s limit=%d min_score=%d",
             args.niche, args.location, requested, args.limit, args.min_score)

    seen = SeenStore(Path(args.outdir) / "seen_hashes.json") if not args.no_dedup else None
    if seen:
        log.info("Dedup store: %d eerder geziene posts geladen", len(seen))

    raw_total: list[RawPost] = []
    polite = PoliteSession(HttpConfig(request_delay=2.0))

    for source_name in requested:
        fetch = REGISTRY[source_name]
        queries = queries_per_source.get(source_name) or []
        if not queries:
            log.warning("Geen queries voor source=%s — skipped", source_name)
            continue
        for q in queries:
            t0 = time.monotonic()
            try:
                # location is al verwerkt in expand_queries() — niet nogmaals toevoegen
                posts = fetch(q, limit=args.limit, location=None, session=polite)
            except Exception as e:
                log.warning("Source %s crashte op q=%r: %s", source_name, q, e)
                posts = []
            dt = time.monotonic() - t0
            log.info("[%s] q=%r -> %d posts in %.1fs", source_name, q, len(posts), dt)
            for p in posts:
                if seen and seen.has(p.fingerprint()):
                    continue
                raw_total.append(p)

    in_memory_seen: set[str] = set()
    leads: list[Lead] = []
    skipped_promo_or_info = 0
    skipped_low_score = 0

    for raw in raw_total:
        fp = raw.fingerprint()
        if fp in in_memory_seen:
            continue
        in_memory_seen.add(fp)
        cleaned = clean_post(raw)
        full_text = cleaned["full"]
        if not is_potential_lead(full_text):
            skipped_promo_or_info += 1
            continue
        score, breakdown = score_post(cleaned, niche_keywords=keywords_required)
        if score < args.min_score:
            skipped_low_score += 1
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
            niche=args.niche,
            author=raw.author,
            created_at=raw.created_at,
        ))
        if seen:
            seen.add(fp)

    if args.facebook_file:
        fb_posts = load_posts_from_file(args.facebook_file)
        log.info("Facebook handmatige posts geladen: %d", len(fb_posts))
        fb_leads = analyze_manual_posts(
            fb_posts,
            niche=args.niche,
            niche_keywords=keywords_required,
            min_score=args.min_score,
        )
        leads.extend(fb_leads)

    if seen:
        seen.save()
        log.info("Dedup store opgeslagen: %d entries", len(seen))

    log.info("Pipeline klaar: raw=%d, leads=%d (skip promo/info=%d, skip lowscore=%d)",
             len(raw_total), len(leads), skipped_promo_or_info, skipped_low_score)

    paths = export_leads(leads, niche=args.niche, outdir=args.outdir)
    print()
    print("=" * 70)
    print(f"  CONSUMER LEAD RADAR  —  niche={args.niche}  location={args.location}")
    print("=" * 70)
    print(f"  Raw posts gevonden : {len(raw_total)}")
    print(f"  Promo/info gefilt. : {skipped_promo_or_info}")
    print(f"  Onder min-score    : {skipped_low_score}")
    print(f"  Leads in output    : {len(leads)}")
    hot = sum(1 for l in leads if l.intent == "hot")
    warm = sum(1 for l in leads if l.intent == "warm")
    cold = sum(1 for l in leads if l.intent == "cold")
    print(f"     hot  (>=70)     : {hot}")
    print(f"     warm (40-69)    : {warm}")
    print(f"     cold (<40)      : {cold}")
    print(f"  CSV  : {paths.get('csv')}")
    if "json" in paths:
        print(f"  JSON : {paths.get('json')}")
    print("=" * 70)
    if leads:
        top = sorted(leads, key=lambda l: l.score, reverse=True)[:5]
        print("  Top 5 leads:")
        for l in top:
            city = l.city or "—"
            print(f"   [{l.score:>3}] {l.intent:<4} {l.source:<11} {city:<14}  {l.title[:60]}")
            print(f"         {l.url}")
    print()
    return 0


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)
    try:
        return run_pipeline(args)
    except KeyboardInterrupt:
        log.warning("Onderbroken door gebruiker")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
