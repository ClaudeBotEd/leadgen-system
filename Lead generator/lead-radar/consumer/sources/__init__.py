"""Source registry — koppelt naam -> fetch functie.

Elke source-module exporteert `fetch(query, *, limit, location=None, **kw) -> list[RawPost]`.
"""
from __future__ import annotations

from typing import Callable

from . import reddit as _reddit
from . import tweakers as _tweakers
from . import bouwinfo as _bouwinfo
from . import google as _google
from . import marktplaats as _marktplaats
from . import facebook as _facebook

REGISTRY: dict[str, Callable] = {
    "reddit": _reddit.fetch,
    "tweakers": _tweakers.fetch,
    "bouwinfo": _bouwinfo.fetch,
    "google": _google.fetch,
    "marktplaats": _marktplaats.fetch,
}

ALL_SOURCES: list[str] = list(REGISTRY.keys())

analyze_manual_posts = _facebook.analyze_manual_posts

__all__ = ["REGISTRY", "ALL_SOURCES", "analyze_manual_posts"]
