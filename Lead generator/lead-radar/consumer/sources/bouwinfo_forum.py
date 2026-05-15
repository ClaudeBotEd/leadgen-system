"""Bouwinfo.be deelforum-crawler — diepere ingestion dan de search-source.

De bestaande `bouwinfo.py` doet `/?s=<query>` en is afhankelijk van
Bouwinfo's interne zoekmachine.  Deze source crawlt direct
`/categories/<path>` voor RECENTE topics in niche-specifieke deelfora:

  /categories/technieken/verwarming-en-koeling/warmtepompen
  /categories/technieken/elektriciteit/zonne-energie
  /categories/technieken/sanitair
  /categories/technieken/ventilatie
  /categories/ruwbouw/isolatie

Thread-URLs hebben format `/bouwforum/threads/<id>` (live geverifieerd
2026-05-14).  We pakken alle thread-anchors per pagina; processor-laag
filtert verder op intent.

Source-naam in RawPost is `bouwinfo` (zelfde dedup-namespace als search-
source) zodat een thread die in beide strategieën opduikt niet dubbel
verwerkt wordt.
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from .. import RawPost
from ..utils import PoliteSession, HttpConfig

log = logging.getLogger("consumer.sources.bouwinfo_forum")

BASE = "https://www.bouwinfo.be"
SOURCE_NAME = "bouwinfo"  # zelfde namespace als search-source voor dedup
# Match zowel relatieve (`/bouwforum/threads/123`) als absolute
# (`https://www.bouwinfo.be/bouwforum/threads/123`) hrefs.  Bouwinfo
# rendert sinds ~mei-2026 alleen absolute URLs in category-pages.
THREAD_PATH_RE = re.compile(r"(?:https?://[^/]+)?/bouwforum/threads/(\d+)")


def _parse_category_page(html: str) -> list[RawPost]:
    """Plukt thread-anchors uit een /categories/-pagina.

    Robuust tegen HTML-wijzigingen: we selecteren op URL-pattern in
    href, niet op CSS-classes.  Bouwinfo gebruikt geen specifieke
    .topicRow class; titel-text wordt direct uit de anchor gehaald.
    """
    if not html:
        return []
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        log.warning("Bouwinfo forum parsing fout: %s", e)
        return []

    seen: set[str] = set()
    out: list[RawPost] = []
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        m = THREAD_PATH_RE.match(href)
        if not m:
            continue
        thread_id = m.group(1)
        rid = f"{SOURCE_NAME}:{thread_id}"
        if rid in seen:
            continue
        seen.add(rid)
        title = (a.get_text() or "").strip()
        if not title or len(title) < 3:
            continue
        out.append(RawPost(
            id=rid,
            source=SOURCE_NAME,
            url=f"{BASE}{href}",
            title=title,
            text="",
            metadata={"strategy": "category-crawl"},
        ))
    return out


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    """Fetch topics uit een Bouwinfo-categorie.

    `query` moet een category-pad zijn, bv:
      '/categories/technieken/verwarming-en-koeling/warmtepompen'

    Onbekend formaat → graceful lege lijst (geen request).  `location`
    wordt genegeerd: forum-categorieën zijn niet locatie-specifiek.
    """
    if not query or not query.startswith("/categories/"):
        log.debug("bouwinfo_forum: skipping non-category query %r", query)
        return []

    sess = session or PoliteSession(HttpConfig(request_delay=3.0))
    url = f"{BASE}{query}"
    resp = sess.get(url)
    if resp is None:
        return []
    posts = _parse_category_page(resp.text)[:limit]
    log.info("Bouwinfo forum: %d posts uit %s", len(posts), query)
    return posts
