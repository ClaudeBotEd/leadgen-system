"""Web search source — heet `google` per spec, gebruikt onder de motorkap
DuckDuckGo (gratis, geen API key, al beschikbaar via duckduckgo_search lib).

Voordeel boven echte Google: geen captcha, geen ban-risk.  Identieke
results voor lead-discovery (we zoeken vooral site:reddit.com / tweakers).

Als duckduckgo_search niet geïnstalleerd is valt dit module gracefully terug
op een lege lijst — niet crashen.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Iterable

from .. import RawPost

log = logging.getLogger("consumer.sources.google")

try:
    from duckduckgo_search import DDGS  # type: ignore
    _HAS_DDG = True
except Exception:
    DDGS = None  # type: ignore
    _HAS_DDG = False


def _short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:12]


def _ddg_search(query: str, max_results: int) -> Iterable[dict]:
    if not _HAS_DDG:
        return []
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, region="nl-nl", safesearch="moderate", max_results=max_results))
    except Exception as e:
        log.warning("DDG search faalde voor q=%r: %s", query, e)
        return []


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          **_: object) -> list[RawPost]:
    if not _HAS_DDG:
        log.warning("duckduckgo_search niet geinstalleerd — google source skipped")
        return []

    q = query
    if location and "{location}" in q:
        q = q.replace("{location}", location)
    elif location:
        q = f"{q} {location}"

    raw = _ddg_search(q, max_results=limit)
    out: list[RawPost] = []
    for r in raw:
        url = r.get("href") or r.get("url") or ""
        title = r.get("title") or ""
        body = r.get("body") or r.get("description") or ""
        if not url:
            continue
        rid = f"google:{_short_hash(url)}"
        out.append(RawPost(
            id=rid,
            source="google",
            url=url,
            title=title,
            text=body,
            created_at=None,
            metadata={"query": q},
        ))

    log.info("Google/DDG: %d resultaten voor q=%r", len(out), q)
    return out
