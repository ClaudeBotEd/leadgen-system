"""Klusidee.nl deelforum-crawler — NL-tegenhanger van bouwinfo_forum.

Klusidee draait op XenForo:
  - Subforums: /Forum/forum/<slug>.<id>/
  - Threads:   /Forum/topic/<slug>.<id>/  (optioneel /post-<post-id>)

Live-geverifieerd 2026-05-14.

Niche → relevante deelfora (in queries.yaml als klusidee_subforums):

  cv:        /Forum/forum/cv-ketels-gaskachels-en-geisers.33/
             /Forum/forum/verwarming-inclusief-leidingwerk.5/
  airco:     /Forum/forum/elektrisch-verlichting-en-ventilatie.11/
  zonnepanelen: /Forum/forum/elektrisch-verlichting-en-ventilatie.11/
  renovatie: /Forum/forum/draagconstructie.13/
             /Forum/forum/binnenmuren-wanden-en-plafonds.8/
             /Forum/forum/badkamer-waterleiding-en-afvoer.2/
             /Forum/forum/keuken.3/
             /Forum/forum/dak-en-schoorsteen.4/

(Warmtepomp valt onder cv/verwarming — geen aparte categorie op klusidee.)

Source-naam in RawPost is `klusidee` (eigen dedup-namespace; geen
search-source als alternatief).
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from .. import RawPost
from ..utils import PoliteSession, HttpConfig

log = logging.getLogger("consumer.sources.klusidee_forum")

BASE = "https://www.klusidee.nl"
SOURCE_NAME = "klusidee"
# XenForo: /Forum/topic/<slug>.<id>/  — <id> is wat we als RawPost.id willen
THREAD_PATH_RE = re.compile(r"^/Forum/topic/[^/]+?\.(\d+)/?")


def _parse_category_page(html: str) -> list[RawPost]:
    """Plukt thread-anchors uit een /Forum/forum/<slug>.<id>/ pagina.

    Robuust tegen HTML-wijzigingen: we selecteren op URL-pattern in
    href, niet op CSS-classes (XenForo skin-themes verschillen).
    """
    if not html:
        return []
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        log.warning("Klusidee forum parsing fout: %s", e)
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
            metadata={"strategy": "subforum-crawl"},
        ))
    return out


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    """Fetch topics uit een Klusidee-deelforum.

    `query` moet een subforum-pad zijn, bv:
      '/Forum/forum/cv-ketels-gaskachels-en-geisers.33/'

    Onbekend formaat → graceful lege lijst (geen request).  `location`
    wordt genegeerd: deelfora zijn niet locatie-specifiek.
    """
    if not query or not query.startswith("/Forum/forum/"):
        log.debug("klusidee_forum: skipping non-subforum query %r", query)
        return []

    sess = session or PoliteSession(HttpConfig(request_delay=3.0))
    url = f"{BASE}{query}"
    resp = sess.get(url)
    if resp is None:
        return []
    posts = _parse_category_page(resp.text)[:limit]
    log.info("Klusidee forum: %d posts uit %s", len(posts), query)
    return posts
