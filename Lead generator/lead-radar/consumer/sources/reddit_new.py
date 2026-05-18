"""Reddit /r/<sub>/new.json crawler — direct recent feed, géén query.

Aanvullend op reddit.py (search-based).  Voor HIGH-INTENT subs zoals
r/Klussers, r/Offertes, r/DIYNL is bijna elke post een intent-signaal —
keyword-filtering werkt averechts (skipt nieuwe leads die nét niet de
exacte term gebruiken).  Deze source pakt ALLE recente posts; processor-
laag (intent_classifier + scorer) filtert verder.

Endpoint:
    https://www.reddit.com/r/<sub>/new.json?limit=<n>

Source-naam blijft 'reddit' (gedeelde dedup-namespace met reddit.py
search-source).  Een post die in beide strategieën opduikt wordt
automatisch eenmalig verwerkt.
"""
from __future__ import annotations

import logging

from .. import RawPost
from ..utils import PoliteSession, HttpConfig
from . import reddit as _reddit_search  # voor _parse_listing hergebruik

log = logging.getLogger("consumer.sources.reddit_new")

BASE = "https://www.reddit.com"


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    """Fetch recente posts uit een subreddit zonder keyword-filter.

    `query`: subreddit-naam (met of zonder 'r/' prefix).
    `location`: genegeerd — feeds zijn niet locatie-specifiek.
    """
    sub = (query or "").strip().lstrip("/").lstrip("r/").strip("/")
    if not sub:
        log.debug("reddit_new: empty sub name, skipping")
        return []

    sess = session or PoliteSession(HttpConfig(request_delay=2.5))
    url = f"{BASE}/r/{sub}/new.json"
    params = {"limit": min(100, max(1, limit))}
    resp = sess.get(url, params=params, accept_json=True)
    if resp is None:
        return []

    try:
        data = resp.json()
    except Exception as e:
        log.warning("reddit_new: invalid JSON van r/%s: %s", sub, e)
        return []

    raw = _reddit_search._parse_listing(data)[:limit]
    # Override source and source_id: this feed is reddit_new, not reddit.
    posts = [
        RawPost(
            id=p.id,
            source="reddit_new",
            source_id=f"reddit_new:r/{sub}",
            url=p.url,
            title=p.title,
            text=p.text,
            author=p.author,
            created_at=p.created_at,
            metadata=p.metadata,
        )
        for p in raw
    ]
    log.info("Reddit /r/%s/new: %d posts", sub, len(posts))
    return posts
