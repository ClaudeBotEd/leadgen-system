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
    "google": _google.fetch,
    "marktplaats": _marktplaats.fetch,
    "2dehands": _tweedehands.fetch,
}

ALL_SOURCES: list[str] = list(REGISTRY.keys())

# Sources die `location` negeren of waar location-suffix de resultaten niet
# beïnvloedt — bij multi-locatie daily-runs draaien ze 1× per niche, NIET
# 1× per niche-locatie.  Bespaart 95%+ verspilde HTTP calls bij --locations all.
#
# Verifieerd in source-code:
#  - tweakers: keywords + page params, geen geo-filter (tweakers.py:117)
#  - reddit_new: /r/<sub>/new.json — sub-feed, location genegeerd (reddit_new.py:34)
#  - bouwinfo, bouwinfo_forum: BE nationaal forum, geen city-routing
#  - klusidee_forum: NL nationaal forum, geen city-routing (klusidee_forum.py:92)
NATIONAL_SOURCES: frozenset[str] = frozenset({
    "tweakers",
    "reddit_new",
    "bouwinfo",
    "bouwinfo_forum",
    "klusidee_forum",
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

__all__ = [
    "REGISTRY",
    "ALL_SOURCES",
    "NATIONAL_SOURCES",
    "LOCATION_AWARE_SOURCES",
    "analyze_manual_posts",
]
