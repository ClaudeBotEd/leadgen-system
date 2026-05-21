"""Source registry — koppelt naam -> fetch functie.

Elke source-module exporteert `fetch(query, *, limit, location=None, **kw) -> list[RawPost]`.
"""
from __future__ import annotations

from typing import Callable

from . import reddit as _reddit
from . import reddit_new as _reddit_new
from . import tweakers as _tweakers
from . import bouwinfo as _bouwinfo
from . import bouwinfo_forum as _bouwinfo_forum
from . import klusidee_forum as _klusidee_forum
from . import ouders_forum as _ouders_forum
from . import google as _google
from . import marktplaats as _marktplaats
from . import tweedehands as _tweedehands
from . import facebook as _facebook

REGISTRY: dict[str, Callable] = {
    "reddit": _reddit.fetch,
    "reddit_new": _reddit_new.fetch,
    "tweakers": _tweakers.fetch,
    "bouwinfo": _bouwinfo.fetch,
    "bouwinfo_forum": _bouwinfo_forum.fetch,
    "klusidee_forum": _klusidee_forum.fetch,
    "ouders_forum": _ouders_forum.fetch,
    "google": _google.fetch,
    "marktplaats": _marktplaats.fetch,
    "2dehands": _tweedehands.fetch,
}

ALL_SOURCES: list[str] = list(REGISTRY.keys())

# Canonical source baseline for proof-sprint rehearsal runs.  Keep this
# separate from ALL_SOURCES so rehearsal commands can stay intentionally
# narrow without changing default source registry behavior.
PROOF_SPRINT_SOURCES: list[str] = ["reddit", "reddit_new"]

# Sources die `location` negeren of waar location-suffix de resultaten niet
# beïnvloedt — bij multi-locatie daily-runs draaien ze 1× per niche, NIET
# 1× per niche-locatie.  Bespaart 95%+ verspilde HTTP calls bij --locations all.
#
# Verifieerd in source-code:
#  - tweakers: keywords + page params, geen geo-filter (tweakers.py:117)
#  - reddit_new: /r/<sub>/new.json — sub-feed, location genegeerd (reddit_new.py:34)
#  - bouwinfo, bouwinfo_forum: BE nationaal forum, geen city-routing
#  - klusidee_forum: NL nationaal forum, geen city-routing (klusidee_forum.py:92)
#  - ouders_forum: NL nationaal forum, geen city-routing (ouders_forum.py)
NATIONAL_SOURCES: frozenset[str] = frozenset({
    "tweakers",
    "reddit_new",
    "bouwinfo",
    "bouwinfo_forum",
    "klusidee_forum",
    "ouders_forum",
})

# Sources waar location-string het query-resultaat WEL beïnvloedt:
#  - reddit (search): location wordt aan q-text geappend (reddit.py:79)
#  - google/DDG: location in zoekstring, regio-bias resultaten (google.py:75-78)
#  - marktplaats, 2dehands: location in zoekquery, plaatsfilter (marktplaats.py:100)
LOCATION_AWARE_SOURCES: frozenset[str] = frozenset({
    "reddit",
    "google",
    "marktplaats",
    "2dehands",
})

analyze_manual_posts = _facebook.analyze_manual_posts


# ─── Runtime dead-source health detector ───────────────────────────────
#
# Telt consecutive 0-yield invocations per source per run.  Bij
# DEAD_THRESHOLD hits-in-a-row markeert source als 'dead': dispatcher
# slaat 'm dan over voor resterende niche-loc combos.  Voorkomt dat
# een HTML-breakage, vervallen API-key of geblokte host wall-clock
# blijft kosten voor de rest van de run.

DEAD_THRESHOLD = 3
_source_health: dict[str, int] = {}


def reset_source_health(source: str | None = None) -> None:
    """Reset per-source 0-yield counters.

    Args:
        source: If None, reset all sources. Otherwise reset only this source.
                Aan te roepen bij start van een run of voor specifieke troubleshooting.
    """
    if source is None:
        _source_health.clear()
    else:
        _source_health[source] = 0


def mark_source_yield(name: str, yield_count: int) -> None:
    """Log uitkomst van source-call.  yield_count > 0 reset counter; 0 verhoogt."""
    if yield_count > 0:
        _source_health[name] = 0
    else:
        _source_health[name] = _source_health.get(name, 0) + 1


def is_source_dead(name: str) -> bool:
    """True als source DEAD_THRESHOLD keer achter elkaar 0 yields gaf."""
    return _source_health.get(name, 0) >= DEAD_THRESHOLD


__all__ = [
    "REGISTRY",
    "ALL_SOURCES",
    "PROOF_SPRINT_SOURCES",
    "NATIONAL_SOURCES",
    "LOCATION_AWARE_SOURCES",
    "DEAD_THRESHOLD",
    "analyze_manual_posts",
    "reset_source_health",
    "mark_source_yield",
    "is_source_dead",
]
