#!/usr/bin/env python3
"""Lead Radar — main orchestrator.

Usage:
    python run.py --niche warmtepomp --location amsterdam --max-results 25
    python run.py --niche airco --location antwerpen --country be
    python run.py --help
"""

from __future__ import annotations
import sys
import argparse
from pathlib import Path
from urllib.parse import urlparse

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from utils.rate_limiter import RateLimiter
from scrapers import ddg_search, website_scraper
from scoring.intent_scorer import score_lead, load_keywords
from output.exporter import export_leads, append_to_master


def load_config(path: Path | None = None) -> dict:
    path = path or (HERE / "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_queries(niche_cfg: dict, location: str) -> list[str]:
    raw = niche_cfg.get("queries", [])
    return [q.format(location=location) for q in raw]


DEFAULT_ALLOWED_TLDS = {"nl", "be", "eu", "com", "net", "org", "info", "io"}


def filter_urls(
    results: list[dict],
    blacklist: list[str],
    dedup: bool = True,
    allowed_tlds: set[str] | None = None,
) -> list[dict]:
    """Filter URLs op blacklist + dedup + (optioneel) allowed TLDs."""
    allowed_tlds = allowed_tlds if allowed_tlds is not None else DEFAULT_ALLOWED_TLDS
    seen_domains: set[str] = set()
    out: list[dict] = []
    for r in results:
        url = r.get("url", "")
        if not url:
            continue
        host = urlparse(url).netloc.lower().replace("www.", "")
        if not host:
            continue
        # TLD filter — alleen NL/BE/EU/INT bedrijven
        tld = host.rsplit(".", 1)[-1] if "." in host else ""
        if allowed_tlds and tld not in allowed_tlds:
            continue
        # Blacklist
        if any(host == bd or host.endswith("." + bd) for bd in blacklist):
            continue
        # Dedup
        if dedup and host in seen_domains:
            continue
        seen_domains.add(host)
        out.append(r)
    return out


def run(
    niche: str,
    location: str,
    max_results: int = 25,
    country: str = "nl",
    config_path: Path | None = None,
    enrich: bool = True,
    min_score_override: int | None = None,
    output_format: str = "csv",
) -> list[dict]:
    config = load_config(config_path)
    niches = config.get("niches", {})
    if niche not in niches:
        raise ValueError(f"Niche '{niche}' niet gevonden in config.yaml. Beschikbaar: {list(niches.keys())}")

    niche_cfg = niches[niche]
    queries = build_queries(niche_cfg, location)
    if not queries:
        raise ValueError(f"Niche '{niche}' heeft geen queries gedefinieerd.")

    region = "nl-nl" if country.lower() == "nl" else "be-nl" if country.lower() == "be" else "wt-wt"
    delay = config.get("scraper", {}).get("request_delay", 2.0)
    limiter = RateLimiter(min_delay=delay)

    print(f"\n=== LEAD RADAR ===")
    print(f"Niche:     {niche}")
    print(f"Location:  {location}")
    print(f"Country:   {country}")
    print(f"Queries:   {len(queries)}")
    for q in queries:
        print(f"  - {q}")
    print()

    print("--- Step 1: DuckDuckGo search ---")
    raw_results = ddg_search.search(
        queries=queries,
        max_results=max_results,
        region=region,
        rate_limiter=limiter,
    )
    print(f"  raw results: {len(raw_results)}")

    blacklist = config.get("filtering", {}).get("blacklist_domains", [])
    dedup = config.get("filtering", {}).get("dedup", True)
    filtered = filter_urls(raw_results, blacklist, dedup=dedup)
    print(f"  after filter+dedup: {len(filtered)}")

    if not filtered:
        print("[!] Geen resultaten na filtering. Probeer andere keywords of locatie.")
        return []

    if enrich:
        print(f"\n--- Step 2: Website enrichment ({len(filtered)} sites) ---")
        enriched = website_scraper.enrich_results(filtered, rate_limiter=limiter, max_subpages=2)
    else:
        enriched = [{"url": r["url"], "title": r.get("title", ""), "snippet": r.get("snippet", ""),
                     "source": r.get("source", ""), "query": r.get("query", "")} for r in filtered]

    print(f"\n--- Step 3: Intent scoring ---")
    keywords = load_keywords()
    for lead in enriched:
        score, breakdown = score_lead(lead, niche=niche, location=location, config=config, keywords=keywords)
        lead["intent_score"] = score
        lead["score_breakdown"] = breakdown
        lead["niche"] = niche

    enriched.sort(key=lambda x: x.get("intent_score", 0), reverse=True)

    min_score = min_score_override if min_score_override is not None else config.get("filtering", {}).get("min_score", 30)
    high_quality = [lead for lead in enriched if lead.get("intent_score", 0) >= min_score]
    print(f"  scored {len(enriched)} leads, {len(high_quality)} >= {min_score}")

    print(f"\n--- Step 4: Export ---")
    out_dir = HERE / config.get("output", {}).get("directory", "data")
    fmt = output_format or config.get("output", {}).get("format", "csv")
    export_leads(high_quality, niche=niche, location=location, fmt=fmt, directory=out_dir)

    print(f"\n--- Top 5 leads ---")
    for i, lead in enumerate(high_quality[:5], 1):
        print(f"  #{i}  [{lead.get('intent_score',0):3d}] {lead.get('company_name','?')[:50]}")
        print(f"        {lead.get('email','-')} | {lead.get('url','')}")

    print(f"\n=== Klaar - {len(high_quality)} qualified leads ===\n")
    return high_quality


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lead Radar - gratis lead generation voor NL/BE HVAC")
    parser.add_argument("--niche", required=True, help="warmtepomp | airco | zonnepanelen | hvac_generiek")
    parser.add_argument("--location", required=True, help="Plaatsnaam, bv 'amsterdam' of 'antwerpen'")
    parser.add_argument("--country", default="nl", choices=["nl", "be"], help="Land code")
    parser.add_argument("--max-results", type=int, default=25, help="Max resultaten per zoekopdracht")
    parser.add_argument("--no-enrich", action="store_true", help="Skip website enrichment")
    parser.add_argument("--min-score", type=int, help="Override min score voor filtering")
    parser.add_argument("--format", default="csv", choices=["csv", "json", "both"], help="Output formaat")
    parser.add_argument("--master", action="store_true", help="Append ook aan data/leads_master.csv")
    args = parser.parse_args(argv)

    try:
        leads = run(
            niche=args.niche,
            location=args.location,
            max_results=args.max_results,
            country=args.country,
            enrich=not args.no_enrich,
            min_score_override=args.min_score,
            output_format=args.format,
        )

        if args.master and leads:
            master_path = HERE / "data" / "leads_master.csv"
            append_to_master(leads, master_path=master_path)

        return 0
    except KeyboardInterrupt:
        print("\n[!] Onderbroken door user")
        return 130
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
