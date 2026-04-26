"""Tweakers Gathering of Tomorrow forum source.

Tweakers heeft geen publieke API.  We gebruiken hun Algemene Zoeken-pagina:
  https://gathering.tweakers.net/forum/find?keywords=...

Antwoorden zijn HTML — we parsen met BeautifulSoup.  Bij wijzigingen aan de
HTML structuur faalt parsing maar returnen we []  — geen crash.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import RawPost
from ..utils import PoliteSession, HttpConfig

log = logging.getLogger("consumer.sources.tweakers")

BASE = "https://gathering.tweakers.net"
SEARCH_URL = f"{BASE}/forum/find"


def _extract_thread_id(href: str) -> str | None:
    if not href:
        return None
    m = re.search(r"/forum/(?:list_messages|view_message)/(\d+)", href)
    if m:
        return m.group(1)
    return href


def _parse_search(html: str) -> list[RawPost]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[RawPost] = []

    candidates = soup.select(
        "div.searchresult, li.result, tr.topic, div.result, article.result"
    )
    if not candidates:
        candidates = soup.select("a[href*='/forum/list_messages']")

    for node in candidates:
        if node.name == "a":
            link = node
            container = node
        else:
            link = node.select_one("a[href*='/forum/list_messages'], a[href*='/forum/view_message']")
            container = node
        if not link:
            continue
        href = link.get("href") or ""
        if not href:
            continue
        url = urljoin(BASE, href)
        title = (link.get_text() or "").strip()
        if not title:
            continue
        snippet = ""
        snip_el = container.select_one(".snippet, .description, p")
        if snip_el:
            snippet = snip_el.get_text(" ", strip=True)
        author = None
        auth_el = container.select_one(".author, .username, .userlink")
        if auth_el:
            author = auth_el.get_text(strip=True) or None

        thread_id = _extract_thread_id(href) or url
        out.append(RawPost(
            id=f"tweakers:{thread_id}",
            source="tweakers",
            url=url,
            title=title,
            text=snippet,
            author=author,
            created_at=None,
            metadata={},
        ))
    return out


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    sess = session or PoliteSession(HttpConfig(request_delay=3.0))
    q = f"{query} {location}".strip() if location else query

    out: list[RawPost] = []
    for page in range(1, 4):
        if len(out) >= limit:
            break
        params = {"keywords": q, "page": page}
        resp = sess.get(SEARCH_URL, params=params)
        if resp is None:
            log.warning("Tweakers gaf geen response voor q=%r page=%d", q, page)
            break
        try:
            page_posts = _parse_search(resp.text)
        except Exception as e:
            log.warning("Tweakers parsing fout: %s", e)
            page_posts = []
        if not page_posts:
            break
        out.extend(page_posts)

    seen: set[str] = set()
    deduped: list[RawPost] = []
    for p in out:
        if p.id in seen:
            continue
        seen.add(p.id)
        deduped.append(p)
        if len(deduped) >= limit:
            break

    log.info("Tweakers: %d posts voor q=%r", len(deduped), q)
    return deduped
