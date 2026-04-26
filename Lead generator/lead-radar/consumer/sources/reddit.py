"""Reddit source — gebruikt de publieke JSON API (geen auth, geen API key).

Endpoints:
  https://www.reddit.com/search.json?q=...&sort=new&limit=...
  https://www.reddit.com/r/<sub>/search.json?q=...&restrict_sr=on&sort=new

Reddit eist een echte User-Agent en geeft 429 bij te snel pollen — daarom
gebruiken we PoliteSession met sleep + retry.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from .. import RawPost
from ..utils import PoliteSession, HttpConfig

log = logging.getLogger("consumer.sources.reddit")

BASE = "https://www.reddit.com"
DEFAULT_SUBS = [
    "thenetherlands", "Netherlands", "belgium", "belgium2", "dutch",
    "amsterdam", "rotterdam", "utrecht", "eindhoven", "antwerpen", "gent",
    "DIYNL", "duurzaam",
]


def _to_iso(unix_ts: float | None) -> str | None:
    if unix_ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(unix_ts), tz=timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return None


def _parse_listing(json_data: dict) -> list[RawPost]:
    out: list[RawPost] = []
    children = (json_data.get("data") or {}).get("children") or []
    for child in children:
        d = (child or {}).get("data") or {}
        if d.get("over_18"):
            continue
        post_id = d.get("id") or ""
        permalink = d.get("permalink") or ""
        url = f"{BASE}{permalink}" if permalink else d.get("url") or ""
        title = d.get("title") or ""
        body = d.get("selftext") or ""
        author = d.get("author") or None
        created = _to_iso(d.get("created_utc"))
        sub = d.get("subreddit") or ""
        score = d.get("score") or 0
        if not post_id:
            continue
        out.append(RawPost(
            id=post_id,
            source="reddit",
            url=url,
            title=title,
            text=body,
            author=author,
            created_at=created,
            metadata={"subreddit": sub, "score": int(score)},
        ))
    return out


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          subreddits: list[str] | None = None, session: PoliteSession | None = None,
          **_: object) -> list[RawPost]:
    """Zoek Reddit voor `query`. Doorzoek meegegeven subs en algemeen.

    Returns nooit None — bij errors gewoon lege lijst.
    """
    sess = session or PoliteSession(HttpConfig(request_delay=2.5))
    subs = subreddits or DEFAULT_SUBS
    q = query
    if location:
        q = f"{query} {location}"

    found: list[RawPost] = []
    seen_ids: set[str] = set()

    targets: list[tuple[str, dict]] = []
    for sub in subs:
        targets.append((
            f"{BASE}/r/{sub}/search.json",
            {"q": q, "restrict_sr": "on", "sort": "new", "limit": min(25, limit)},
        ))
    targets.append((
        f"{BASE}/search.json",
        {"q": q, "sort": "new", "limit": min(50, limit)},
    ))

    for url, params in targets:
        if len(found) >= limit:
            break
        resp = sess.get(url, params=params, accept_json=True)
        if resp is None:
            continue
        try:
            data = resp.json()
        except Exception:
            log.warning("Reddit gaf geen JSON: %s", url)
            continue
        for post in _parse_listing(data):
            if post.id in seen_ids:
                continue
            seen_ids.add(post.id)
            found.append(post)
            if len(found) >= limit:
                break

    log.info("Reddit: %d posts voor query=%r (subs=%d)", len(found), q, len(subs))
    return found
