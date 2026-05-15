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

try:
    from duckduckgo_search.exceptions import RatelimitException  # type: ignore
except Exception:
    # Fallback: vang alleen generieke Exception als lib oud/afwezig is
    class RatelimitException(Exception):  # type: ignore
        pass

# Rate-limit guard: DDG blokt agressief bij >100 req/h.  Bij --daily
# --locations all worden 1000+ DDG-calls gedaan; zodra DDG eenmaal
# blokkeert hangen alle volgende calls op interne backoff.  Na N
# rate-limits in deze run skippen we DDG volledig zodat de rest van
# de pipeline doorloopt zonder cascade.
_RATELIMIT_THRESHOLD = 2
_DDG_TIMEOUT_SECONDS = 10
_ratelimit_state: dict[str, int] = {"count": 0}


def reset_ratelimit_state() -> None:
    """Reset DDG rate-limit counter — aan te roepen bij start van een run."""
    _ratelimit_state["count"] = 0


def _short_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:12]


def _ddg_search(query: str, max_results: int) -> Iterable[dict]:
    if not _HAS_DDG:
        return []
    if _ratelimit_state["count"] >= _RATELIMIT_THRESHOLD:
        # Hard-skip: voorkomt cascade van trage zombie-calls bij DDG-block
        return []
    try:
        with DDGS(timeout=_DDG_TIMEOUT_SECONDS) as ddgs:
            return list(ddgs.text(
                query, region="nl-nl", safesearch="moderate",
                max_results=max_results,
            ))
    except RatelimitException as e:
        _ratelimit_state["count"] += 1
        log.warning(
            "DDG rate-limit hit (%d/%d) op q=%r: %s — verdere DDG-calls "
            "worden geskipt bij overschrijden threshold",
            _ratelimit_state["count"], _RATELIMIT_THRESHOLD, query, e,
        )
        return []
    except Exception as e:
        log.warning("DDG search faalde voor q=%r: %s", query, e)
        return []


_FORUM_URL_PATTERNS = [
    "reddit.com/r/",
    "gathering.tweakers.net/forum/",
    "tweakers.net/forum/",
    "bouwinfo.be/",
    "forum.",
    "/forum/",
    "/topic/",
    "/thread/",
    "/discussion/",
    "facebook.com/groups/",
    "hvac-forum",
    "klimaatforum",
    "forums.",
]


def _is_post_url(url: str) -> bool:
    """Filter: alleen forum/post-stijl URLs.  Skipt vendor homepages."""
    if not url:
        return False
    u = url.lower()
    return any(p in u for p in _FORUM_URL_PATTERNS)


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

    raw = _ddg_search(q, max_results=limit * 3)  # over-fetch want we filteren ~70% weg
    out: list[RawPost] = []
    skipped = 0
    for r in raw:
        url = r.get("href") or r.get("url") or ""
        title = r.get("title") or ""
        body = r.get("body") or r.get("description") or ""
        if not url:
            continue
        if not _is_post_url(url):
            skipped += 1
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
        if len(out) >= limit:
            break

    log.info("Google/DDG: %d post-URLs voor q=%r (skipped %d non-forum)", len(out), q, skipped)
    return out
