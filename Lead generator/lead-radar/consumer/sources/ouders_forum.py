"""Ouders.nl deelforum-crawler — gezinnen-segment voor home-installation intent.

Ouders.nl is een NL community-site voor gezinnen met een actief
"huis-tuin-en-keuken" subforum waar threads voorkomen over
vloerverwarming, koelen huis (airco), zonnepanelen, glasvezel, energie.
Klein-volume vergeleken met Klusidee/Bouwinfo, maar:

  - geen vendor-ads (community-moderatie filtert dat)
  - hoge intent-dichtheid (consumenten met concrete vragen)
  - doelgroep heeft typisch koopkracht + eigen huis

Source-naam in RawPost is `ouders` (eigen dedup-namespace).

URL-pattern (live geverifieerd 2026-05-15):
  Subforum:  /forum/<sub>           bv. /forum/huis-tuin-en-keuken
  Thread:    /forum/<sub>/<slug>    bv. /forum/huis-tuin-en-keuken/...
  Paginatie: /forum/<sub>/<slug>?page=N
"""
from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from .. import RawPost
from ..utils import PoliteSession, HttpConfig

log = logging.getLogger("consumer.sources.ouders_forum")

BASE = "https://www.ouders.nl"
SOURCE_NAME = "ouders"
# Match een thread-pad: /forum/<sub>/<slug>  — geen extra segmenten,
# geen query-string, geen fragment.  Dit sluit de subforum-index zelf,
# paginatie-links én sub-deeper paden uit.
THREAD_PATH_RE = re.compile(r"^/forum/([^/?#]+)/([^/?#]+)$")
# Slugs die geen echte threads zijn maar UI-CTAs (zelfde URL-shape
# als threads, maar leiden naar een create-form ipv een topic).
CTA_SLUGS: frozenset[str] = frozenset({"nieuw"})


def _parse_subforum_page(html: str) -> list[RawPost]:
    """Plukt thread-anchors uit een /forum/<sub> pagina.

    Robuust tegen HTML-wijzigingen: we selecteren op URL-pattern in href,
    niet op CSS-classes (skin-themes wijzigen).  Cijfer-titels (paginatie
    "1", "2") en korte titels (< 3 tekens) worden afgevangen als ruis.
    """
    if not html:
        return []
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        log.warning("Ouders forum parsing fout: %s", e)
        return []

    seen: set[str] = set()
    out: list[RawPost] = []
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        m = THREAD_PATH_RE.match(href)
        if not m:
            continue
        sub, slug = m.group(1), m.group(2)
        if slug in CTA_SLUGS:
            continue
        rid = f"{SOURCE_NAME}:{sub}/{slug}"
        if rid in seen:
            continue
        title = (a.get_text() or "").strip()
        if not title or len(title) < 3 or title.isdigit():
            continue
        seen.add(rid)
        out.append(RawPost(
            id=rid,
            source=SOURCE_NAME,
            source_id=f"ouders_forum:{sub}",
            url=f"{BASE}{href}",
            title=title,
            text="",
            metadata={"strategy": "subforum-crawl", "subforum": sub},
        ))
    return out


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    """Fetch threads uit een Ouders.nl-subforum.

    `query` moet een /forum/<sub> pad zijn, bv:
      '/forum/huis-tuin-en-keuken'

    Onbekend formaat → graceful lege lijst (geen request).  `location`
    wordt genegeerd: subforums zijn niet locatie-specifiek.
    """
    if not query or not query.startswith("/forum/") or "/" in query[len("/forum/"):]:
        log.debug("ouders_forum: skipping non-subforum query %r", query)
        return []

    sess = session or PoliteSession(HttpConfig(request_delay=3.0))
    url = f"{BASE}{query}"
    resp = sess.get(url)
    if resp is None:
        return []
    posts = _parse_subforum_page(resp.text)[:limit]
    log.info("Ouders forum: %d posts uit %s", len(posts), query)
    return posts
