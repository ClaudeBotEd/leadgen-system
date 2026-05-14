"""Regression tests voor dispatch-mappings tussen queries.yaml en sources.

Twee silent-gap patronen worden hier afgedwongen:

1. expand_queries() — als een source in REGISTRY zit moet hij óók queries
   krijgen. Originele bug: '2dehands' had geen mapping → silent skip.

2. extra_kwargs_for_source() — sommige sources verwachten configuratie
   uit `defaults` in queries.yaml (bv. reddit krijgt subreddits-lijst).
   Bug: defaults.reddit_subreddits werd nooit doorgegeven aan
   reddit.fetch() → r/Klussers, r/Offertes, r/heatpumps stilletjes
   genegeerd, source viel terug op hardcoded DEFAULT_SUBS in reddit.py.
"""
from __future__ import annotations

import pytest

from run_consumer import expand_queries, extra_kwargs_for_source, parse_locations
from consumer.sources import ALL_SOURCES


@pytest.fixture
def niche_cfg() -> dict:
    """Minimale niche-config met alle query-buckets non-leeg."""
    return {
        "keywords_required": ["warmtepomp"],
        "queries_text": [
            "warmtepomp installateur gezocht",
            "warmtepomp offerte",
        ],
        "google_queries": [
            'site:reddit.com warmtepomp {location}',
            '"warmtepomp installateur" {location}',
        ],
        "marktplaats_queries": [
            "warmtepomp installateur gezocht",
            "warmtepomp monteur gevraagd",
        ],
        "bouwinfo_categories": [
            "/categories/technieken/verwarming-en-koeling/warmtepompen",
            "/categories/technieken/verwarming-en-koeling",
        ],
        "klusidee_subforums": [
            "/Forum/forum/cv-ketels-gaskachels-en-geisers.33/",
            "/Forum/forum/verwarming-inclusief-leidingwerk.5/",
        ],
    }


def test_expand_queries_covers_every_registered_source(niche_cfg: dict) -> None:
    """Geen silent gaps: elke source in ALL_SOURCES krijgt een queries-list.

    Falen betekent dat de dispatch-loop in run_consumer.py die source
    zal overslaan zonder error — exact het 2dehands-bug-pattern.
    """
    result = expand_queries(niche_cfg, location="nederland", max_queries=50)
    missing = [s for s in ALL_SOURCES if s not in result]
    assert not missing, (
        f"expand_queries mist mapping voor sources {missing}; "
        f"deze sources worden silent geskipt in run_consumer.py."
    )


def test_expand_queries_2dehands_falls_back_to_marktplaats(niche_cfg: dict) -> None:
    """Bij ontbreken van tweedehands_queries: 2dehands gebruikt marktplaats_queries.
    Backward-compat — voorheen was er nooit een aparte tweedehands_queries field."""
    # niche_cfg fixture heeft GEEN tweedehands_queries → fallback verwacht
    result = expand_queries(niche_cfg, location="antwerpen", max_queries=50)
    assert "2dehands" in result
    assert result["2dehands"], "2dehands kreeg lege queries"
    assert result["2dehands"] == result["marktplaats"], (
        "Zonder tweedehands_queries moet 2dehands marktplaats_queries gebruiken"
    )


def test_expand_queries_2dehands_uses_dedicated_be_queries() -> None:
    """Met tweedehands_queries gezet: 2dehands gebruikt die, NIET marktplaats.
    Zo kunnen we BE-spreektaal (premie, vlaamse fraseringen) los aansturen."""
    niche_cfg = {
        "queries_text": ["warmtepomp installateur"],
        "marktplaats_queries": ["warmtepomp installateur gezocht"],
        "tweedehands_queries": [
            "warmtepomp installateur antwerpen",
            "warmtepomp premie vlaanderen",
        ],
    }
    result = expand_queries(niche_cfg, location="gent", max_queries=50)
    assert result["2dehands"] == [
        "warmtepomp installateur antwerpen",
        "warmtepomp premie vlaanderen",
    ]
    # Marktplaats blijft NL-set houden
    assert result["marktplaats"] == ["warmtepomp installateur gezocht"]


def test_expand_queries_all_sources_get_nonempty_lists(niche_cfg: dict) -> None:
    """Voor een niche met queries in alle drie buckets moet elke source ≥1 query krijgen."""
    result = expand_queries(niche_cfg, location="amsterdam", max_queries=50)
    for source in ALL_SOURCES:
        qs = result.get(source) or []
        assert qs, f"Source {source!r} kreeg lege query-list bij volledige niche-config"


# ─── extra_kwargs_for_source — source-specific dispatch kwargs ───────────────


def test_reddit_uses_defaults_subreddits() -> None:
    """defaults.reddit_subreddits MOET doorgegeven worden aan reddit.fetch."""
    defaults = {"reddit_subreddits": ["thenetherlands", "Vlaanderen", "heatpumps"]}
    assert extra_kwargs_for_source("reddit", defaults) == {
        "subreddits": ["thenetherlands", "Vlaanderen", "heatpumps"]
    }


def test_reddit_no_defaults_returns_empty_so_fetch_uses_its_own_defaults() -> None:
    """Bij ontbrekende of lege subs-config geen kwarg → reddit.fetch valt
    terug op DEFAULT_SUBS in reddit.py (graceful)."""
    assert extra_kwargs_for_source("reddit", {}) == {}
    assert extra_kwargs_for_source("reddit", {"reddit_subreddits": []}) == {}
    assert extra_kwargs_for_source("reddit", {"reddit_subreddits": None}) == {}


@pytest.mark.parametrize("source", ["tweakers", "bouwinfo", "google", "marktplaats", "2dehands"])
def test_non_reddit_sources_get_no_extra_kwargs(source: str) -> None:
    """Alleen reddit consumeert reddit_subreddits — andere sources mogen
    er niet door verstoord raken (TypeError op onbekende kwarg)."""
    defaults = {"reddit_subreddits": ["x", "y"]}
    assert extra_kwargs_for_source(source, defaults) == {}


# ─── parse_locations — multi-location support voor --daily ───────────────────


def test_parse_locations_comma_separated_string() -> None:
    """--locations 'nederland,vlaanderen' wordt 2-element lijst."""
    assert parse_locations("nederland,vlaanderen") == ["nederland", "vlaanderen"]


def test_parse_locations_strips_whitespace_and_empty_entries() -> None:
    """Tolerant voor user-typed input: spaties, dubbele komma's."""
    assert parse_locations(" amsterdam ,  rotterdam ,, brussel ") == [
        "amsterdam", "rotterdam", "brussel"
    ]


def test_parse_locations_none_uses_fallback() -> None:
    """Als --locations leeg is maar --location wel gezet, gebruik die."""
    assert parse_locations(None, fallback="brussel") == ["brussel"]


def test_parse_locations_no_value_no_fallback_defaults_to_nederland() -> None:
    """Beide leeg → daily mode default: nederland."""
    assert parse_locations(None) == ["nederland"]
    assert parse_locations("") == ["nederland"]


def test_parse_locations_single_value_no_comma() -> None:
    """--locations 'vlaanderen' (geen komma) is geldige single-elem lijst."""
    assert parse_locations("vlaanderen") == ["vlaanderen"]


# ─── parse_locations met presets (uit queries.yaml defaults) ─────────────────


def test_parse_locations_preset_expands_to_full_list() -> None:
    """--locations 'nl' → cities_nl uit defaults; geen letterlijke 'nl' query."""
    presets = {"nl": ["amsterdam", "rotterdam", "utrecht"]}
    assert parse_locations("nl", presets=presets) == ["amsterdam", "rotterdam", "utrecht"]


def test_parse_locations_preset_is_case_insensitive() -> None:
    """User mag --locations 'NL' of 'All' typen."""
    presets = {"all": ["amsterdam", "antwerpen"]}
    assert parse_locations("ALL", presets=presets) == ["amsterdam", "antwerpen"]
    assert parse_locations("All", presets=presets) == ["amsterdam", "antwerpen"]


def test_parse_locations_unknown_string_falls_through_to_literal() -> None:
    """Onbekende waarde is geen preset → letterlijke komma-split (backward compat)."""
    presets = {"nl": ["amsterdam"]}
    assert parse_locations("vlaanderen,brussel", presets=presets) == ["vlaanderen", "brussel"]


def test_parse_locations_no_presets_means_no_preset_expansion() -> None:
    """Zonder presets-arg gedraagt zich exact als voorheen."""
    assert parse_locations("nl") == ["nl"]  # letterlijk, geen expansie
