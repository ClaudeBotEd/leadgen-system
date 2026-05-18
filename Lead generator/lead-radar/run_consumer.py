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
import math
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from consumer import Lead, RawPost, intent_from_score  # noqa: E402
from consumer.sources import (  # noqa: E402
    REGISTRY, ALL_SOURCES, NATIONAL_SOURCES, LOCATION_AWARE_SOURCES,
    analyze_manual_posts,
    reset_source_health, mark_source_yield, is_source_dead,
)
from consumer.sources.facebook import load_posts_from_file  # noqa: E402
from consumer.sources.facebook.queue import drain as drain_fb_queue  # noqa: E402
from consumer.sources.reddit_author import enrich_author  # noqa: E402
from consumer.processor import (  # noqa: E402
    TextSignatureStore,
    check_hardblock,
    clean_post,
    combine_score,
    generate_message,
    is_potential_lead,
    score_post,
    should_verify,
    smart_summary,
    verify_post,
    apply_recency_boost,
    AGED_OUT,
    apply_source_weight,
    load_source_weights,
    is_cross_run_duplicate,
    record_lead_signature,
    is_author_repeat,
    record_author_post,
    SOURCES_WITH_AUTHOR,
    is_sellable,
)
from consumer.output.telegram import (  # noqa: E402
    RunStats,
    SourceStat,
    send_run_digest,
)
from consumer.processor.llm_verifier import (  # noqa: E402
    get_run_stats,
    reset_run_counters,
)
from consumer.sources.google import reset_ratelimit_state as _reset_ddg_ratelimit  # noqa: E402
from consumer.output import (  # noqa: E402
    export_leads,
    send_lead_alert,
    sync_to_sheets,
)
from consumer.utils import PoliteSession, HttpConfig, SeenStore  # noqa: E402
from consumer.logging_setup import setup_logging  # noqa: E402

HOT_ALERT_THRESHOLD = 80

# Mockable monotonic-clock voor wall-clock budget enforcement.  Tests
# overschrijven via monkeypatch om elapsed-tijd te simuleren.
_monotonic = time.monotonic

log = logging.getLogger("consumer.cli")

DEFAULT_QUERIES_YAML = HERE / "consumer" / "queries.yaml"
DEFAULT_OUTDIR = HERE / "data" / "leads" / "consumer"


def _check_env(args) -> tuple[bool, list[str]]:
    """Return (ok, errors). Sheets vars required unless --no-sheets is set."""
    errors: list[str] = []
    if not getattr(args, "no_sheets", False):
        if not os.environ.get("LEAD_RADAR_SPREADSHEET_ID"):
            errors.append(
                "LEAD_RADAR_SPREADSHEET_ID is missing. Set it in .env "
                "(launchd does NOT source ~/.zshrc) or pass --no-sheets."
            )
        if not os.environ.get("LEAD_RADAR_GS_CREDENTIALS"):
            errors.append(
                "LEAD_RADAR_GS_CREDENTIALS is missing. Set absolute quoted "
                "path in .env or pass --no-sheets."
            )
    return (not errors, errors)

# Defaults voor --daily mode (production usage)
DAILY_NICHES = ["warmtepomp", "airco", "zonnepanelen", "cv", "renovatie"]
DAILY_LOCATION = "nederland"
DAILY_LIMIT = 25
DAILY_MAX_QUERIES = 12  # hogere variatie -> meer raw posts -> meer leads
DAILY_MIN_SCORE = 60    # >=60 voor OPPORTUNITIES tab; sheets.py filtert <60 weg
DAILY_MAX_AGE_DAYS = 7


def _setup_logging(verbose: bool) -> str:
    return setup_logging(verbose=verbose)


def load_config(path: Path) -> dict:
    if not path.exists():
        log.warning("queries.yaml niet gevonden: %s — gebruik defaults", path)
        return {"defaults": {}, "niches": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Consumer lead radar — vindt high-intent NL/BE leads")

    # Daily preset (alle niches in 1 command)
    p.add_argument("--daily", action="store_true",
                   help="Daily preset: alle niches, score>=60 (OPPORTUNITIES; 70+→ALL LEADS, "
                        "80+→HOT LEADS), time filter 7d, sheets sync. Geen --niche nodig.")

    # Niche-specifiek (of via --daily over alle niches)
    p.add_argument("--niche", default=None,
                   help="Niche (warmtepomp/airco/zonnepanelen/cv/renovatie). Vereist tenzij --daily.")
    p.add_argument("--location", default=None,
                   help="Locatie (bv 'nederland', 'amsterdam'). Optioneel. "
                        "Voor multi-locatie daily-runs: gebruik --locations.")
    p.add_argument("--locations", default=None,
                   help="Komma-lijst locaties voor --daily mode "
                        "(bv 'nederland,vlaanderen,amsterdam'). "
                        "Presets uit queries.yaml defaults: "
                        "'nl' (alle NL-steden), 'be' (alle BE-steden), "
                        "'all' (NL+BE). "
                        "Default: --location of 'nederland'. "
                        "Vermenigvuldigt query-volume per locatie — "
                        "let op rate-limits + LLM-budget.")
    p.add_argument("--limit", type=int, default=50,
                   help="Max raw posts per source-query (default 50)")
    p.add_argument("--sources", default="",
                   help=f"Komma-lijst sources. Default = alles. Beschikbaar: {','.join(ALL_SOURCES)}")
    p.add_argument("--min-score", type=int, default=30,
                   help="Minimum score om in output op te nemen (default 30; --daily dwingt 60)")
    p.add_argument("--max-age-days", type=int, default=0,
                   help="Filter posts ouder dan N dagen weg (0 = uit; --daily dwingt 7)")
    p.add_argument("--queries-file", default=str(DEFAULT_QUERIES_YAML))
    p.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    p.add_argument("--facebook-file", default=None,
                   help="Optioneel pad naar tekstbestand met handmatige FB-posts "
                        "(legacy alias voor --manual-file --manual-platform facebook)")
    p.add_argument("--manual-file", default=None,
                   help="Pad naar tekstbestand met handmatig gekopieerde posts "
                        "van een high-risk platform (geen scraping). "
                        "Posts gescheiden door lege regel of '---'.")
    p.add_argument("--manual-platform", default="facebook",
                   help="Platform-label voor --manual-file (bv 'facebook', "
                        "'linkedin', 'instagram', 'tiktok', 'whatsapp', "
                        "'telegram'). Geen whitelist. Default: facebook.")
    p.add_argument("--no-dedup", action="store_true",
                   help="Cross-run dedup uit (negeer seen_hashes.json)")
    p.add_argument("--max-queries", type=int, default=8,
                   help="Max # tekst-queries per niche (default 8)")
    p.add_argument("--max-runtime-minutes", type=float, default=0.0,
                   help="Wall-clock budget voor --daily mode (default 0 = uit). "
                        "Bij overschrijding: skip resterende niches, push wat we hebben. "
                        "Aangeraden bij --locations all: 90.")

    # Google Sheets
    p.add_argument("--sheets", action="store_true",
                   help="Push leads naar Google Sheets (--daily zet dit automatisch)")
    p.add_argument("--no-sheets", action="store_true",
                   help="Skip Google Sheets sync (env validation will pass without Sheets vars)")
    p.add_argument("--spreadsheet-id", default=None,
                   help="Spreadsheet ID. Default: env LEAD_RADAR_SPREADSHEET_ID")
    p.add_argument("--credentials", default=None,
                   help="Pad naar Google service-account JSON")

    # Quality kwaliteits-lagen
    p.add_argument("--no-hardblock", action="store_true",
                   help="Skip aggregator/spam hard-block filter (default: aan)")
    p.add_argument("--no-fuzzy-dedup", action="store_true",
                   help="Skip MinHash-style fuzzy dedup (default: aan)")
    p.add_argument("--dedup-threshold", type=float, default=0.70,
                   help="Jaccard threshold voor fuzzy dedup (default 0.70)")
    p.add_argument("--no-llm", action="store_true",
                   help="Skip Claude LLM-verifier op borderline scores")
    p.add_argument("--llm-min-score", type=int, default=40,
                   help="Min score voor LLM-verification (default 40)")
    p.add_argument("--llm-max-score", type=int, default=75,
                   help="Max score voor LLM-verification (default 75)")
    p.add_argument("--llm-max-eur", type=float, default=0.0,
                   help="LLM budget cap per run in EUR (default 0 = uit). "
                        "Bij overschrijden van geschatte spend: verdere "
                        "verify_post() calls returnen skipped(budget_exhausted) "
                        "en de pipeline gebruikt regex-score. Aanbevolen bij "
                        "--daily --locations all: 5.00.")
    p.add_argument("--enrich-authors", action="store_true",
                   help="Reddit author-history check inschakelen (default UIT — "
                        "rate-limited door Reddit, gaf 429s op daily runs)")
    p.add_argument("--no-author-enrich", action="store_true",
                   help="[DEPRECATED] Was vroeger nodig om enrichment uit te zetten; "
                        "enrichment is nu standaard uit. Gebruik --enrich-authors voor opt-in.")
    p.add_argument("--no-telegram", action="store_true",
                   help="Skip Telegram alerts voor HOT leads")
    p.add_argument("--telegram-threshold", type=int, default=80,
                   help="Min score voor Telegram alert (default 80)")

    p.add_argument("--dry-run", action="store_true",
                   help="Run pipeline maar push NIETS naar externe systemen "
                        "(geen Sheets sync, geen Telegram alerts). "
                        "CSV/JSON exports gebeuren wel. Combineer met "
                        "--no-llm voor kosten-vrije test.")
    p.add_argument("--check-env-only", action="store_true",
                   help="Validate env vars and exit (used by test harness and CI checks)")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    if not args.daily and not args.niche:
        p.error("Geef --niche <name> of --daily")
    return args


def parse_locations(
    value: str | None,
    fallback: str | None = None,
    *,
    presets: dict[str, list[str]] | None = None,
) -> list[str]:
    """Parse komma-string naar lijst van locaties voor multi-location daily-run.

    Tolerant voor user-input:
    - Spaties rond elk item worden gestript
    - Lege segmenten (dubbele komma's, trailing comma's) genegeerd

    Presets (case-insensitive): bv {"nl": [..steden..], "be": [...], "all": [...]}.
    Als `value` exact matcht met een preset-key, wordt de bijbehorende
    lijst geretourneerd.  Anders valt het terug op letterlijke komma-split.

    Fallback-order: value > fallback > 'nederland'.  Daily mode mag nooit
    een lege lijst krijgen — dan zou run_daily 0 iteraties doen.
    """
    if value:
        if presets:
            preset_key = value.strip().lower()
            if preset_key in presets and presets[preset_key]:
                return list(presets[preset_key])
        items = [s.strip() for s in value.split(",") if s.strip()]
        if items:
            return items
    if fallback:
        return [fallback]
    return ["nederland"]


def scale_max_queries_for_locations(base: int, n_locations: int) -> int:
    """Reduceer max_queries-per-source bij multi-location daily-runs.

    Bij --locations all (23 locs) × max_queries=12 krijg je 276 query-
    permutaties per source per niche.  Location-suffix levert al variatie,
    dus query-diversiteit kan omlaag zonder coverage te verliezen.

    Formule: max(3, base // ceil(sqrt(n))).  Sqrt-gradient is minder
    aggressief dan lineair: 5 locs → 1/3 reductie; 100 locs → 1/10.
    Bodem 3 voorkomt dat we volledig terugvallen op de eerste query.
    Gecapt op `base` zodat lage user-input nooit OMHOOG scaled.
    """
    if n_locations <= 1:
        return base
    divisor = math.ceil(math.sqrt(n_locations))
    scaled = max(3, base // divisor)
    return min(base, scaled)


def extra_kwargs_for_source(source_name: str, defaults: dict,
                            *, daily: bool = False) -> dict:
    """Source-specific kwargs uit queries.yaml `defaults`-section.

    Voorkomt dat per-source config silent dead code wordt.  Reddit
    gebruikt kwargs uit defaults (subreddits-lijst).  Marktplaats/
    2dehands krijgen `deep_variants=False` in daily mode om de 3-
    variant loop ("q gezocht", "q gevraagd") over te slaan.

    Andere sources krijgen lege dict terug zodat `**extra_kwargs`
    veilig spreidt.
    """
    if source_name == "reddit":
        subs = defaults.get("reddit_subreddits")
        if subs:
            return {"subreddits": list(subs)}
    if daily and source_name in ("marktplaats", "2dehands"):
        return {"deep_variants": False}
    return {}


def expand_queries(niche_cfg: dict, location: str | None, max_queries: int) -> dict[str, list[str]]:
    text_qs = (niche_cfg.get("queries_text") or [])[:max_queries]
    google_qs = (niche_cfg.get("google_queries") or [])[:max_queries]
    market_qs = (niche_cfg.get("marktplaats_queries") or [])[:max_queries]
    tweedehands_qs = (niche_cfg.get("tweedehands_queries") or [])[:max_queries]

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

    bouwinfo_cats = niche_cfg.get("bouwinfo_categories") or []
    klusidee_subs = niche_cfg.get("klusidee_subforums") or []
    ouders_subs = niche_cfg.get("ouders_subforums") or []
    reddit_new_subs = niche_cfg.get("reddit_new_subs") or []
    return {
        "reddit": loc_subst(text_qs),
        # reddit_new pakt /r/<sub>/new.json — query is een subreddit-naam,
        # niet een keyword.  Voor high-intent subs (Klussers/Offertes/DIYNL).
        "reddit_new": reddit_new_subs,
        "tweakers": text_qs,
        "bouwinfo": text_qs,
        "bouwinfo_forum": bouwinfo_cats,
        "klusidee_forum": klusidee_subs,
        "ouders_forum": ouders_subs,
        "google": loc_subst(google_qs) if google_qs else loc_subst(text_qs),
        "marktplaats": market_qs or text_qs,
        # 2dehands krijgt BE-specifieke set als die er is; anders fallback op
        # marktplaats_queries (NL-spreektaal werkt deels ook op 2dehands).
        "2dehands": tweedehands_qs or market_qs or text_qs,
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


def _process_post(
    *,
    raw: RawPost,
    niche: str,
    data_dir: Path,
    now: datetime | None = None,
    no_llm: bool = False,
    weights: dict[str, float] | None = None,
    cross_run_store: Path | None = None,
    author_store: Path | None = None,
    min_score: int = 60,
    llm_min_score: int = 40,
    llm_max_score: int = 75,
    enrich_authors: bool = False,
    no_author_enrich: bool = True,
    niche_keywords: list[str] | None = None,
) -> Lead | None:
    """Process a single RawPost through the full per-post pipeline.

    Returns a Lead if the post passes all filters, None otherwise.
    Steps:
      1. clean + regex score
      2. LLM verify (40-75 band)
      3. recency boost (drop if AGED_OUT)
      4. source-credibility weight (clamped 0-100)
      5. min_score threshold
      6. Layer-2 cross-run dedup
      7. Layer-3 author-signature dedup (only SOURCES_WITH_AUTHOR)
      8. build Lead
      9. sellability gate (demote hot → warm, never drop)
      10. record dedup signatures
      11. return Lead
    """
    now = now or datetime.now(timezone.utc)
    if weights is None:
        weights = load_source_weights(config_path=HERE / "config.yaml")
    cross_run_store = cross_run_store or (data_dir / "dedup_store.jsonl")
    author_store = author_store or (data_dir / "author_signature.jsonl")
    keywords = niche_keywords or [niche]

    # Step 1: clean + regex score
    cleaned = clean_post(raw)
    score, breakdown = score_post(
        cleaned,
        niche_keywords=keywords,
        created_at=raw.created_at,
    )

    # Step 2: LLM verify if in borderline band
    if (not no_llm) and should_verify(score, min_score=llm_min_score, max_score=llm_max_score):
        verdict = verify_post(
            title=cleaned["title"], text=cleaned["text"],
            city=cleaned["city"], niche=niche,
            regex_score=score, regex_breakdown=breakdown,
        )
        if verdict.available:
            new_score = combine_score(score, verdict)
            breakdown["llm_verdict"] = f"{verdict.kind}/{verdict.confidence:.2f}"
            if new_score != score:
                breakdown["llm_adjustment"] = new_score - score
            score = new_score

    # Step 3: recency boost — drop if AGED_OUT (> 14d)
    boosted = apply_recency_boost(score=score, created_at=raw.created_at, now=now)
    if boosted is AGED_OUT:
        return None
    score = boosted  # type: ignore[assignment]

    # Step 4: source-credibility weight (clamped 0-100)
    score = apply_source_weight(score=score, source=raw.source_id or raw.source, weights=weights)

    # Step 5: min_score threshold
    if score < min_score:
        return None

    # Step 6: Layer-2 cross-run dedup
    text_for_dedup = cleaned.get("full") or cleaned.get("text") or ""
    if is_cross_run_duplicate(text=text_for_dedup, store_path=cross_run_store):
        return None

    # Step 7: Layer-3 author-signature dedup (only for sources that carry reliable authors)
    if raw.source in SOURCES_WITH_AUTHOR and raw.author:
        if is_author_repeat(author=raw.author, niche=niche, store_path=author_store):
            return None

    # Step 8: build Lead
    lead = Lead(
        id=raw.id,
        source=raw.source,
        source_id=raw.source_id,
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
    )

    # Step 9: sellability gate — demote hot → warm when required fields missing
    gate = is_sellable(lead)
    if not gate.ok and lead.intent == "hot":
        lead.intent = "warm"
        lead.breakdown["sellability_missing"] = gate.missing

    # Step 10: record dedup signatures (after all filters pass)
    record_lead_signature(
        lead_id=lead.id,
        text=text_for_dedup,
        source=raw.source_id or raw.source,
        niche=niche,
        store_path=cross_run_store,
        now=now,
    )
    if raw.source in SOURCES_WITH_AUTHOR and raw.author:
        record_author_post(
            author=raw.author,
            niche=niche,
            store_path=author_store,
            now=now,
        )

    # Step 11: return Lead
    return lead


def run_one_niche(
    args: argparse.Namespace,
    niche: str,
    *,
    location_override: str | None = None,
    sources_override: list[str] | None = None,
    fb_extra_posts: list[RawPost] | None = None,
) -> list[Lead]:
    """Run pipeline voor 1 niche en returnt de Lead-list.

    location_override: optioneel; als gezet override args.location voor
    deze run.  Gebruikt door run_daily() om over meerdere locaties te
    itereren zonder args te muteren.

    sources_override: optioneel; als gezet bepaalt deze lijst welke
    sources gedraaid worden (i.p.v. args.sources).  Gebruikt door
    run_daily() voor location-aware/national split — nationale sources
    draaien 1× per niche, locatie-afhankelijke 1× per niche-loc.

    fb_extra_posts: optioneel; pre-drained RawPost-lijst uit
    ``data/fb_queue/`` (van de standalone FB scraper runner).  Gefilterd
    op ``metadata.niche == niche`` zodat alleen de relevante posts mee
    door dedup/hardblock/score gaan.  Drain gebeurt 1× per CLI-run in
    main(), zodat bij --daily met N niches de queue niet N× wordt
    leeggehaald (`drain` verplaatst files naar processed/).
    """
    cfg = load_config(Path(args.queries_file))
    niches = cfg.get("niches") or {}
    defaults_cfg = cfg.get("defaults") or {}
    if niche not in niches:
        log.error("Niche %r niet in queries.yaml", niche)
        return []
    niche_cfg = niches[niche]
    keywords_required = niche_cfg.get("keywords_required") or [niche]

    if sources_override is not None:
        requested = list(sources_override)
    else:
        requested = [s.strip() for s in args.sources.split(",") if s.strip()] if args.sources else ALL_SOURCES
    invalid = [s for s in requested if s not in REGISTRY]
    if invalid:
        log.error("Onbekende sources: %s", invalid)
        return []

    location = location_override if location_override is not None else args.location
    queries_per_source = expand_queries(niche_cfg, location, args.max_queries)
    log.info("=== %s @ %s | sources=%s limit=%d min_score=%d max_age_days=%d ===",
             niche, location, requested, args.limit, args.min_score, args.max_age_days)

    seen = SeenStore(Path(args.outdir) / "seen_hashes.json") if not args.no_dedup else None
    if seen:
        log.info("Dedup store: %d eerder geziene posts", len(seen))

    fuzzy_store: TextSignatureStore | None = None
    if not args.no_fuzzy_dedup:
        fuzzy_store = TextSignatureStore(
            path=Path(args.outdir) / "text_signatures.json",
            threshold=args.dedup_threshold,
        )
        log.info("Fuzzy dedup-store: %d eerder gehashte posts (threshold=%.2f)",
                 len(fuzzy_store), args.dedup_threshold)

    author_cache_dir: Path | None = None
    if getattr(args, "enrich_authors", False) and not args.no_author_enrich:
        author_cache_dir = Path(args.outdir) / ".author_cache"

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.max_age_days)) if args.max_age_days > 0 else None

    raw_total: list[RawPost] = []
    polite = PoliteSession(HttpConfig(request_delay=2.0))
    leads: list[Lead] = []

    # try/finally borgt dat dedup-stores worden opgeslagen, ook bij
    # KeyboardInterrupt of crash midden in de loop.  Zonder die garantie
    # raken alle "al-geziene" posts uit deze run kwijt en re-processed
    # de volgende run dezelfde URLs (= dubbele LLM-kosten + dupes in Sheets).
    try:
        for source_name in requested:
            # Runtime dead-source skip: na N opeenvolgende 0-yields wordt
            # source overgeslagen voor rest van de run (consumer/sources
            # health-state).  Voorkomt dat HTML-breakage uren wall-clock kost.
            if is_source_dead(source_name):
                log.info(
                    "[%s] skip — gemarkeerd dead (3+ opeenvolgende 0-yield calls)",
                    source_name,
                )
                continue
            fetch = REGISTRY[source_name]
            queries = queries_per_source.get(source_name) or []
            if not queries:
                continue
            extra = extra_kwargs_for_source(
                source_name, defaults_cfg,
                daily=bool(getattr(args, "daily", False)),
            )
            source_yield = 0  # posts deze run via deze source (na seen-filter)
            for q in queries:
                t0 = time.monotonic()
                try:
                    posts = fetch(q, limit=args.limit, location=None, session=polite, **extra)
                except Exception as e:
                    log.warning("Source %s crashte op q=%r: %s", source_name, q, e)
                    posts = []
                log.info("[%s] q=%r -> %d posts in %.1fs", source_name, q, len(posts), time.monotonic() - t0)
                for p in posts:
                    if seen and seen.has(p.fingerprint()):
                        continue
                    raw_total.append(p)
                    source_yield += 1
            # Mark source-health (cumulatief over niche-loc combos in deze run)
            mark_source_yield(source_name, source_yield)
            # Zero-yield detection: vangt silent breakage van een source af.
            if source_yield == 0:
                log.warning(
                    "[%s] 0 posts uit %d queries — source mogelijk gebroken "
                    "(check HTML structuur, API keys, of rate-limit)",
                    source_name, len(queries),
                )

        # Merge FB-scraper queue posts (pre-drained in main()) — filter op niche
        # zodat warmtepomp-posts niet meelopen in een airco-niche-run.  Posts
        # zonder `metadata.niche` worden niet gematched; de FB-runner zet die
        # tag altijd via TargetSpec.niche.
        if fb_extra_posts:
            matched = [p for p in fb_extra_posts if p.metadata.get("niche") == niche]
            if matched:
                log.info("FB queue: %d posts voor niche=%s mergen naar raw_total",
                         len(matched), niche)
                raw_total.extend(matched)

        in_memory_seen: set[str] = set()
        skipped_promo = skipped_low = skipped_old = 0
        skipped_hardblock = skipped_fuzzy_dup = 0
        skipped_aged_out = skipped_cross_run = skipped_author = 0
        llm_calls = author_calls = 0

        # Load source weights once per niche-run (file read; cached dict).
        _source_weights = load_source_weights(config_path=HERE / "config.yaml")
        _data_dir = Path(args.outdir)
        _cross_run_store = _data_dir / "dedup_store.jsonl"
        _author_store = _data_dir / "author_signature.jsonl"
        _run_now = datetime.now(timezone.utc)

        for raw in raw_total:
            fp = raw.fingerprint()
            if fp in in_memory_seen:
                continue
            in_memory_seen.add(fp)

            if not _is_recent(raw.created_at, cutoff):
                skipped_old += 1
                continue

            if not args.no_hardblock:
                hb = check_hardblock(raw)
                if hb.blocked:
                    skipped_hardblock += 1
                    log.debug("hard-block %s: %s", raw.url, hb.reason)
                    continue

            # Promo-filter: uses cleaned text — run clean_post once here
            # so fuzzy-store can also use the cleaned version.
            cleaned = clean_post(raw)
            if not is_potential_lead(cleaned["full"]):
                skipped_promo += 1
                continue

            if fuzzy_store is not None:
                dup = fuzzy_store.find_duplicate(cleaned["full"])
                if dup is not None:
                    skipped_fuzzy_dup += 1
                    log.debug("fuzzy-dup %s ~ %s (sim=%.2f)", fp, dup[0], dup[1])
                    continue

            # Reddit author enrichment (opt-in via --enrich-authors; legacy path)
            _author_penalty: int = 0
            _author_breakdown: dict = {}
            if getattr(args, "enrich_authors", False) and (not args.no_author_enrich) and raw.source == "reddit" and raw.author:
                profile = enrich_author(raw.author, cache_dir=author_cache_dir)
                if profile.available:
                    author_calls += 1
                    penalty = profile.signal_penalty
                    if penalty:
                        _author_penalty = penalty
                        _author_breakdown = {"author_penalty": penalty, "author_recurring": 1}

            # Core per-post pipeline: score → LLM → recency → weight → dedup → Lead
            lead = _process_post(
                raw=raw,
                niche=niche,
                data_dir=_data_dir,
                now=_run_now,
                no_llm=args.no_llm,
                weights=_source_weights,
                cross_run_store=_cross_run_store,
                author_store=_author_store,
                min_score=args.min_score,
                llm_min_score=args.llm_min_score,
                llm_max_score=args.llm_max_score,
                enrich_authors=getattr(args, "enrich_authors", False),
                no_author_enrich=args.no_author_enrich,
                niche_keywords=keywords_required,
            )
            if lead is None:
                # Distinguish which filter dropped the post for the summary log.
                # We re-compute cheaply to attribute the skip bucket.
                # (Score path is already inside _process_post; we rely on counters
                # being bumped there for the new filters.  For min_score we count below.)
                skipped_low += 1
                continue

            # Apply legacy author penalty to score if enrichment ran
            if _author_penalty:
                lead.score = max(0, lead.score + _author_penalty)
                lead.breakdown.update(_author_breakdown)
                if lead.score < args.min_score:
                    skipped_low += 1
                    continue

            leads.append(lead)
            if seen:
                seen.add(fp)
            if fuzzy_store is not None:
                fuzzy_store.add(fp, cleaned["full"])

            score = lead.score
            if score >= HOT_ALERT_THRESHOLD:
                stad = (lead.city or "—").title()
                summary = smart_summary(
                    text=lead.text or "",
                    title=lead.title or "",
                    city=lead.city,
                    niche=niche,
                )
                print(f"\n🔥 HOT LEAD:\n   {stad} — {summary}\n", flush=True)

                if not args.no_telegram and score >= args.telegram_threshold:
                    try:
                        suggested = generate_message(
                            niche=niche, city=lead.city,
                            text=lead.text, title=lead.title,
                        )
                        result = send_lead_alert(
                            lead, suggested_message=suggested,
                            hot_threshold=args.telegram_threshold,
                        )
                        if result.sent:
                            log.info("Telegram alert verstuurd (mid=%s)", result.message_id)
                        elif result.skipped_reason not in {"below_threshold", "no_credentials"}:
                            log.warning("Telegram skip/err: %s / %s",
                                        result.skipped_reason, result.error)
                    except Exception as e:
                        log.warning("Telegram alert faalde: %s", e)

        if args.facebook_file:
            fb_posts = load_posts_from_file(args.facebook_file)
            log.info("FB handmatig: %d posts", len(fb_posts))
            leads.extend(analyze_manual_posts(
                fb_posts, platform="facebook", niche=niche,
                niche_keywords=keywords_required, min_score=args.min_score,
            ))

        manual_file = getattr(args, "manual_file", None)
        if manual_file:
            manual_platform = getattr(args, "manual_platform", "facebook") or "facebook"
            manual_posts = load_posts_from_file(manual_file)
            log.info("Manual ingest (%s): %d posts", manual_platform, len(manual_posts))
            leads.extend(analyze_manual_posts(
                manual_posts, platform=manual_platform, niche=niche,
                niche_keywords=keywords_required, min_score=args.min_score,
            ))

        log.info(
            "[%s] raw=%d -> leads=%d (promo=%d oud=%d low=%d hardblock=%d fuzzy=%d "
            "llm_calls=%d author_calls=%d)",
            niche, len(raw_total), len(leads), skipped_promo, skipped_old,
            skipped_low, skipped_hardblock, skipped_fuzzy_dup, llm_calls, author_calls,
        )

        export_leads(leads, niche=niche, outdir=args.outdir)
    finally:
        if seen is not None:
            seen.save()
        if fuzzy_store is not None:
            fuzzy_store.save()

    return leads


def _print_summary(niche: str, leads: list[Lead], sheets_result: dict | None) -> None:
    hot = sum(1 for lead in leads if lead.score >= 80)
    warm = sum(1 for lead in leads if 70 <= lead.score < 80)
    opp = sum(1 for lead in leads if 60 <= lead.score < 70)
    print()
    print("─" * 70)
    print(f"  {niche:<14}  leads={len(leads):>3}   HOT={hot:>3}   WARM={warm:>3}   OPP={opp:>3}")
    if sheets_result:
        print(
            f"                  sheets HOT +{sheets_result.get('hot_added',0)}  "
            f"ALL +{sheets_result.get('all_added',0)}  "
            f"OPP +{sheets_result.get('opp_added',0)}"
        )
    if leads:
        top = sorted(leads, key=lambda lead: lead.score, reverse=True)[:3]
        for lead in top:
            mark = "🔥" if lead.score >= 80 else ("⚡" if lead.score >= 70 else "·")
            city = (lead.city or "—")[:12]
            print(f"   {mark} [{lead.score:>3}] {city:<14} {lead.title[:50]}")


def _drain_fb_queue_once(outdir: str | Path) -> list[RawPost]:
    """Drain ``data/fb_queue/`` exactly once per CLI invocation.

    Helper voor run_daily/run_single zodat de drain niet N× per niche-loc
    combo gebeurt (drain verplaatst files naar processed/, dus alleen de
    eerste call zou posts zien).  De returned lijst wordt vervolgens per
    niche gefilterd via `RawPost.metadata["niche"]`.
    """
    fb_queue_dir = HERE / "data" / "fb_queue"
    drained = list(drain_fb_queue(fb_queue_dir))
    if drained:
        log.info("FB queue drained: %d posts uit %s", len(drained), fb_queue_dir)
    return drained


def run_daily(args: argparse.Namespace) -> int:
    """Run alle niches, push naar Sheets.

    Min score = DAILY_MIN_SCORE (60). Sheets verdeelt verder:
      HOT LEADS (>=80) | ALL LEADS (>=70) | OPPORTUNITIES (60-69).
    """
    args.location = args.location or DAILY_LOCATION
    args.limit = args.limit if args.limit != 50 else DAILY_LIMIT
    args.max_queries = args.max_queries if args.max_queries != 8 else DAILY_MAX_QUERIES
    args.min_score = max(args.min_score, DAILY_MIN_SCORE)
    args.max_age_days = args.max_age_days if args.max_age_days > 0 else DAILY_MAX_AGE_DAYS
    args.sheets = True

    # Dry-run: skip externe writes (Sheets + Telegram).  Pipeline runt
    # gewoon door, CSV/JSON exports vinden plaats, zodat operator de
    # output kan inspecteren zonder iets richting prod te pushen.
    if getattr(args, "dry_run", False):
        args.no_telegram = True

    # Reset per-run counters zodat budget cap en cache stats per daily-run
    # zijn, niet cumulatief over meerdere run_daily invocaties in hetzelfde
    # Python-proces (relevant bij testing / langlopende daemon).
    reset_run_counters()
    # Reset DDG rate-limit state — anders blijft skip-mode actief over runs heen.
    _reset_ddg_ratelimit()
    # Reset per-source health counter zodat dead-source skip per run werkt.
    reset_source_health()
    # LLM budget cap: wire CLI flag naar env var die llm_verifier al leest.
    # >0 = enforce; 0 = uit (verwijder env var zodat eerdere run niet doorlekt).
    llm_max_eur = float(getattr(args, "llm_max_eur", 0.0) or 0.0)
    if llm_max_eur > 0.0:
        os.environ["LEAD_RADAR_LLM_BUDGET_EUR"] = str(llm_max_eur)
        log.info("LLM budget cap actief: €%.2f", llm_max_eur)
    else:
        os.environ.pop("LEAD_RADAR_LLM_BUDGET_EUR", None)

    print()
    print("=" * 70)
    _ts_nl = datetime.now(ZoneInfo("Europe/Amsterdam")).strftime("%Y-%m-%d %H:%M")
    dry_tag = "  [DRY-RUN]" if getattr(args, "dry_run", False) else ""
    print(f"  CONSUMER LEAD RADAR  —  DAILY  ({_ts_nl}){dry_tag}")
    print(f"  location={args.location}  limit={args.limit}  min_score>={args.min_score}  max_age={args.max_age_days}d")
    print("=" * 70)

    cfg = load_config(Path(args.queries_file))
    available = list((cfg.get("niches") or {}).keys())
    niches_to_run = [n for n in DAILY_NICHES if n in available]

    defaults_cfg = cfg.get("defaults") or {}
    presets: dict[str, list[str]] = {}
    if defaults_cfg.get("cities_nl"):
        presets["nl"] = list(defaults_cfg["cities_nl"])
    if defaults_cfg.get("cities_be"):
        presets["be"] = list(defaults_cfg["cities_be"])
    if "nl" in presets and "be" in presets:
        presets["all"] = presets["nl"] + presets["be"]

    locations = parse_locations(
        getattr(args, "locations", None),
        fallback=args.location,
        presets=presets,
    )
    if len(locations) > 1:
        log.info("Daily multi-location run: %d locaties (%s)",
                 len(locations),
                 ", ".join(locations) if len(locations) <= 6 else f"{', '.join(locations[:5])}, ...")
        # Auto-scale query-variatie omlaag: locatie levert zelf al variatie.
        scaled_max = scale_max_queries_for_locations(args.max_queries, len(locations))
        if scaled_max != args.max_queries:
            log.info(
                "Auto-scale max_queries: %d → %d (sqrt-reductie voor %d locaties)",
                args.max_queries, scaled_max, len(locations),
            )
            args.max_queries = scaled_max

    # Location-aware dispatch split: nationale forums hebben geen geo-filter,
    # dus per niche 1× draaien.  Location-aware sources (reddit search, google,
    # marktplaats, 2dehands) draaien per locatie.  Bespaart ~95% van runtime
    # bij multi-loc runs op nationale sources.
    requested_for_split = (
        [s.strip() for s in args.sources.split(",") if s.strip()]
        if args.sources else ALL_SOURCES
    )
    national_subset = [s for s in requested_for_split if s in NATIONAL_SOURCES]
    loc_aware_subset = [s for s in requested_for_split if s in LOCATION_AWARE_SOURCES]
    if national_subset and len(locations) > 1:
        log.info(
            "Source split: nationale sources %s 1× per niche; "
            "locatie-afhankelijke %s 1× per niche-locatie (%d locs)",
            national_subset, loc_aware_subset, len(locations),
        )

    grand_total: list[Lead] = []
    sheets_total = {"all_added": 0, "hot_added": 0, "opp_added": 0, "spreadsheet_url": ""}

    # Wall-clock budget: stop met nieuwe niches starten zodra elapsed
    # > budget.  Geen abort midden in niche — sheets-sync per niche
    # zorgt dat tussen-resultaten al gepersist zijn.
    budget_seconds = max(0.0, getattr(args, "max_runtime_minutes", 0.0) or 0.0) * 60.0
    run_start = _monotonic()
    run_start_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Drain FB scraper queue 1× per CLI-run.  Resultaat gefilterd per niche
    # binnen run_one_niche.  Drain verplaatst files naar processed/, dus deze
    # call moet vóór de niche-loop staan en NIET binnen run_one_niche.
    fb_extra_posts = _drain_fb_queue_once(args.outdir)

    for niche_idx, niche in enumerate(niches_to_run):
        if budget_seconds > 0:
            elapsed = _monotonic() - run_start
            if elapsed > budget_seconds:
                remaining = niches_to_run[niche_idx:]
                log.warning(
                    "Wall-clock budget %.0fs overschreden (elapsed=%.0fs) — "
                    "skip %d resterende niches: %s",
                    budget_seconds, elapsed, len(remaining), remaining,
                )
                break
        niche_leads: list[Lead] = []
        # FB-queue posts mogen maar 1× door de niche-loop heen.  We binden
        # ze aan de eerste run_one_niche-call die we voor deze niche doen
        # (national als die er is, anders eerste loc-aware call).  Daarna
        # nullen we de variabele zodat volgende sub-calls niet dezelfde
        # FB-posts re-processen.
        fb_for_niche: list[RawPost] | None = fb_extra_posts
        # Nationale sources: 1× per niche (locatie genegeerd door source-impl,
        # zie consumer/sources/__init__.py NATIONAL_SOURCES toelichting).
        if national_subset:
            leads = run_one_niche(
                args, niche,
                location_override=locations[0],
                sources_override=national_subset,
                fb_extra_posts=fb_for_niche,
            )
            niche_leads.extend(leads)
            fb_for_niche = None  # already consumed
        # Locatie-afhankelijke sources: 1× per locatie.
        if loc_aware_subset:
            for loc in locations:
                leads = run_one_niche(
                    args, niche,
                    location_override=loc,
                    sources_override=loc_aware_subset,
                    fb_extra_posts=fb_for_niche,
                )
                niche_leads.extend(leads)
                fb_for_niche = None  # only first call gets FB posts
        sheets_result = None
        if niche_leads and not getattr(args, "dry_run", False):
            try:
                sheets_result = sync_to_sheets(
                    niche_leads,
                    spreadsheet_id=args.spreadsheet_id,
                    credentials_path=args.credentials,
                )
                sheets_total["all_added"] += sheets_result.get("all_added", 0)
                sheets_total["hot_added"] += sheets_result.get("hot_added", 0)
                sheets_total["opp_added"] += sheets_result.get("opp_added", 0)
                sheets_total["spreadsheet_url"] = sheets_result["spreadsheet_url"]
            except Exception as e:
                log.error("Sheets sync (%s) faalde: %s", niche, e)
        _print_summary(niche, niche_leads, sheets_result)
        grand_total.extend(niche_leads)
        # Progress-heartbeat: per voltooide niche logt elapsed + running ETA
        # zodat operator kan inschatten hoe lang de rest duurt.  Voorkomt
        # "loopt het nog?"-twijfel bij urenlange daily-runs.
        completed = niche_idx + 1
        total_niches = len(niches_to_run)
        elapsed = _monotonic() - run_start
        avg_per_niche = elapsed / completed if completed else 0.0
        remaining = total_niches - completed
        eta = avg_per_niche * remaining
        log.info(
            "[progress] %d/%d done | niche=%s | elapsed=%ds | eta=%ds",
            completed, total_niches, niche, int(elapsed), int(eta),
        )

    hot = sum(1 for lead in grand_total if lead.score >= 80)
    warm = sum(1 for lead in grand_total if 70 <= lead.score < 80)
    opp = sum(1 for lead in grand_total if 60 <= lead.score < 70)
    print()
    print("=" * 70)
    print(f"  TOTAAL leads (score>=60): {len(grand_total)}")
    print(f"     HOT  (>=80, CONTACT) : {hot}")
    print(f"     WARM (70-79, LATER)  : {warm}")
    print(f"     OPP  (60-69, CHECK)  : {opp}")
    if sheets_total["spreadsheet_url"]:
        print(f"  Sheets pushed: HOT +{sheets_total['hot_added']}  "
              f"ALL +{sheets_total['all_added']}  "
              f"OPP +{sheets_total['opp_added']}")
        print(f"  Open  : {sheets_total['spreadsheet_url']}")
    # LLM cost + cache effectiviteit — operator ziet daily spend en kan
    # cache-tuning beslissen zonder Anthropic dashboard te openen.
    llm_stats = get_run_stats()
    total_lookups = llm_stats["cache_hits"] + llm_stats["cache_misses"]
    hit_rate = (llm_stats["cache_hits"] / total_lookups * 100) if total_lookups else 0.0
    print(
        f"  LLM   : {llm_stats['api_calls']} API calls  "
        f"~€{llm_stats['estimated_cost_eur']:.4f}  "
        f"cache_hits={llm_stats['cache_hits']}/{total_lookups} "
        f"({hit_rate:.0f}%)"
    )
    print("=" * 70)

    # Run-digest: Telegram summary van de dagelijkse run (per-source yield, dode
    # sources, totalen).  Alleen bij --daily en tenzij --no-telegram.
    if not getattr(args, "no_telegram", False):
        # Aggregate per-source counts from grand_total leads.
        from collections import defaultdict
        per_source_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {"posts": 0, "leads": 0, "hot": 0}
        )
        for _lead in grand_total:
            _src = _lead.source_id or _lead.source or "unknown"
            per_source_counts[_src]["leads"] += 1
            if _lead.score >= HOT_ALERT_THRESHOLD:
                per_source_counts[_src]["hot"] += 1
        digest_stats = RunStats(
            timestamp=run_start_iso,
            per_source=[
                SourceStat(
                    source=src,
                    posts=counts["leads"],   # posts not tracked separately; use leads count
                    leads=counts["leads"],
                    hot=counts["hot"],
                    dead=is_source_dead(src),
                )
                for src, counts in sorted(per_source_counts.items())
            ],
            apify_spend_used_usd=0.0,
            apify_spend_cap_usd=0.0,
        )
        try:
            send_run_digest(digest_stats, channel="consumer")
        except Exception as e:
            log.warning("Run-digest send failed: %s", e)

    return 0


def run_single(args: argparse.Namespace) -> int:
    if getattr(args, "dry_run", False):
        args.no_telegram = True
        log.info("DRY-RUN: Sheets sync + Telegram alerts uitgezet")
    # Drain FB scraper queue 1× per CLI-run; gefilterd op niche in run_one_niche.
    fb_extra_posts = _drain_fb_queue_once(args.outdir)
    leads = run_one_niche(args, args.niche, fb_extra_posts=fb_extra_posts)
    sheets_result = None
    if args.sheets and leads and not getattr(args, "dry_run", False):
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

    # Fail-fast env validation (must run BEFORE logging setup for error clarity)
    env_ok, env_errors = _check_env(args)
    if not env_ok:
        for err in env_errors:
            print(f"ENV ERROR: {err}", file=sys.stderr)
        sys.exit(2)
    if args.check_env_only:
        print("Env check OK.")
        sys.exit(0)

    run_id = _setup_logging(args.verbose)
    log.info("Lead Radar start (run_id=%s, daily=%s)", run_id, bool(args.daily))
    try:
        if args.daily:
            return run_daily(args)
        return run_single(args)
    except KeyboardInterrupt:
        log.warning("Onderbroken door gebruiker")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
