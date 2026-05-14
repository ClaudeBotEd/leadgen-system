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

analyze_manual_posts = _facebook.analyze_manual_posts

__all__ = ["REGISTRY", "ALL_SOURCES", "analyze_manual_posts"]
