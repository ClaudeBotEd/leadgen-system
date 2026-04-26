"""2dehands.be source — Belgische zuster van marktplaats.nl.

Bestand heet `tweedehands.py` (Python identifiers mogen niet met een
cijfer beginnen).  De source-naam in `RawPost.source` en in `REGISTRY`
blijft `"2dehands"` zoals user-facing verwacht.

Hergebruikt dezelfde fetcher (JSON-blob + HTML fallback) van marktplaats
en wisselt alleen BASE-URL en source-naam.
"""
from __future__ import annotations

from .. import RawPost
from ..utils import PoliteSession
from .marktplaats import fetch_classifieds

BASE = "https://www.2dehands.be"
SOURCE_NAME = "2dehands"


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    return fetch_classifieds(
        BASE, query, source_name=SOURCE_NAME,
        limit=limit, location=location, session=session,
    )
