"""Location-aware source dispatch — voorkomt dat nationale forums 23×
herhaald worden bij --daily --locations all.

Sommige sources negeren `location` volledig (tweakers, reddit_new,
bouwinfo*, klusidee_forum).  Die mogen 1× per niche draaien, niet 1×
per niche-locatie.  Locatie-afhankelijke sources (reddit, google,
marktplaats, 2dehands) blijven per locatie draaien.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest


# ─── Set-level invarianten ──────────────────────────────────────────────


def test_national_sources_set_exists() -> None:
    """`NATIONAL_SOURCES` constante moet importeerbaar zijn."""
    from consumer.sources import NATIONAL_SOURCES
    assert isinstance(NATIONAL_SOURCES, frozenset)
    assert len(NATIONAL_SOURCES) > 0


def test_location_aware_sources_set_exists() -> None:
    """`LOCATION_AWARE_SOURCES` constante moet importeerbaar zijn."""
    from consumer.sources import LOCATION_AWARE_SOURCES
    assert isinstance(LOCATION_AWARE_SOURCES, frozenset)
    assert len(LOCATION_AWARE_SOURCES) > 0


def test_national_includes_tweakers_reddit_new_bouwinfo_klusidee() -> None:
    """Nationale forums: location-string heeft geen invloed op resultaten."""
    from consumer.sources import NATIONAL_SOURCES
    assert "tweakers" in NATIONAL_SOURCES
    assert "reddit_new" in NATIONAL_SOURCES
    assert "bouwinfo" in NATIONAL_SOURCES
    assert "bouwinfo_forum" in NATIONAL_SOURCES
    assert "klusidee_forum" in NATIONAL_SOURCES


def test_location_aware_includes_reddit_google_marktplaats_2dehands() -> None:
    """Locatie-afhankelijk: location-suffix beïnvloedt query of results."""
    from consumer.sources import LOCATION_AWARE_SOURCES
    assert "reddit" in LOCATION_AWARE_SOURCES
    assert "google" in LOCATION_AWARE_SOURCES
    assert "marktplaats" in LOCATION_AWARE_SOURCES
    assert "2dehands" in LOCATION_AWARE_SOURCES


def test_national_and_location_aware_are_disjoint() -> None:
    """Geen source mag in beide sets zitten — dispatch zou ambigu zijn."""
    from consumer.sources import NATIONAL_SOURCES, LOCATION_AWARE_SOURCES
    assert NATIONAL_SOURCES.isdisjoint(LOCATION_AWARE_SOURCES)


def test_national_and_location_aware_cover_all_registry() -> None:
    """Elke source in REGISTRY moet geclassificeerd zijn — geen vergeten source.

    Vangt regressies af wanneer iemand een nieuwe source toevoegt zonder
    'm te classificeren; dispatcher zou hem dan silent skippen.
    """
    from consumer.sources import REGISTRY, NATIONAL_SOURCES, LOCATION_AWARE_SOURCES
    all_classified = NATIONAL_SOURCES | LOCATION_AWARE_SOURCES
    missing = set(REGISTRY.keys()) - all_classified
    assert not missing, f"sources without classification: {missing}"


# ─── Dispatch behavior in run_daily ────────────────────────────────────


def _minimal_args(tmp_path: Path, cfg_path: Path, *,
                  locations: str | None = "amsterdam,rotterdam,utrecht",
                  sources: str = "tweakers,marktplaats") -> argparse.Namespace:
    """Build minimal Namespace zodat run_daily slaagt."""
    return argparse.Namespace(
        # Daily preset gating
        daily=True,
        location=None,
        locations=locations,
        # Dispatch
        sources=sources,
        niche=None,
        limit=50,
        max_queries=8,
        min_score=30,
        max_age_days=0,
        queries_file=str(cfg_path),
        outdir=str(tmp_path),
        # Disable filters / external systems
        no_dedup=True,
        no_fuzzy_dedup=True,
        no_author_enrich=True,
        no_hardblock=True,
        no_llm=True,
        no_telegram=True,
        facebook_file=None,
        manual_file=None,
        manual_platform="facebook",
        dedup_threshold=0.85,
        llm_min_score=40,
        llm_max_score=75,
        telegram_threshold=80,
        sheets=False,
        spreadsheet_id=None,
        credentials=None,
        dry_run=True,
        verbose=False,
    )


def test_run_daily_calls_national_source_once_per_niche(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tweakers (national) mag niet 3× draaien bij 3 locaties — 1× per niche.

    Locatie heeft géén invloed op tweakers query of results (tweakers.py
    appends location maar interne search filtert daar niet op).
    Herhaling = pure verspilling.
    """
    import run_consumer

    cfg_path = tmp_path / "queries.yaml"
    cfg_path.write_text(
        "niches:\n"
        "  cv:\n"
        "    keywords_required: [cv]\n"
        "    queries_text: [cv ketel kapot]\n",
        encoding="utf-8",
    )

    tweakers_calls: list[str | None] = []

    def tracking_tweakers(query, *, limit, location, session, **_):  # noqa: ANN001, ANN201
        tweakers_calls.append(location)
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "tweakers", tracking_tweakers)

    args = _minimal_args(
        tmp_path, cfg_path,
        locations="amsterdam,rotterdam,utrecht",
        sources="tweakers",
    )
    run_consumer.run_daily(args)

    # 1 niche × 1 query × 1 location-call (NOT 3) = 1 call
    assert len(tweakers_calls) == 1, (
        f"tweakers (national) called {len(tweakers_calls)}× — expected 1× per niche regardless of locations. "
        f"calls={tweakers_calls}"
    )


def test_run_daily_calls_location_aware_source_per_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Marktplaats (location-aware) MOET wel per locatie draaien — listings
    zijn locatie-specifiek."""
    import run_consumer

    cfg_path = tmp_path / "queries.yaml"
    cfg_path.write_text(
        "niches:\n"
        "  cv:\n"
        "    keywords_required: [cv]\n"
        "    queries_text: [cv ketel]\n"
        "    marktplaats_queries: [cv ketel]\n",
        encoding="utf-8",
    )

    mp_calls: list[str | None] = []

    def tracking_mp(query, *, limit, location, session, **_):  # noqa: ANN001, ANN201
        mp_calls.append(location)
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "marktplaats", tracking_mp)

    args = _minimal_args(
        tmp_path, cfg_path,
        locations="amsterdam,rotterdam,utrecht",
        sources="marktplaats",
    )
    run_consumer.run_daily(args)

    # 1 niche × 1 query × 3 locations = 3 calls
    assert len(mp_calls) == 3, (
        f"marktplaats (location-aware) called {len(mp_calls)}× — expected 3× (1 per location). "
        f"calls={mp_calls}"
    )
