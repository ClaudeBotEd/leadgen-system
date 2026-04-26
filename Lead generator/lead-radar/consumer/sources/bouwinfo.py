"""Bouwinfo (BE) forum source.

Bouwinfo's forum draait op IPB-achtige software.  De zoekpagina zit op
https://www.bouwinfo.be/?s=<query> of via app=core&module=search.
We proberen beide endpoints en pakken topic-anchors.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .. import RawPost
from ..utils import PoliteSession, HttpConfig

log = logging.getLogger("consumer.sources.bouwinfo")

BASE = "https://www.bouwinfo.be"


def _parse(html: str) -> list[RawPost]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[RawPost] = []

    candidates = soup.select(
        "li.searchresult, article, h2.ipsType_pageTitle, .topicRow, div.cSearch_result, div.search-result"
    )
    if not candidates:
        candidates = soup.select("a[href*='/topic/'], a[href*='/forum/'], a[href*='thread']")

    for node in candidates:
        link = node if node.name == "a" else node.select_one("a")
        if not link:
            continue
        href = link.get("href") or ""
        if not href:
            continue
        url = urljoin(BASE, href)
        title = (link.get_text() or "").strip()
        if not title or len(title) < 8:
            continue

        snippet = ""
        if node is not link:
            for sel in (".snippet", ".description", "p", ".excerpt"):
                el = node.select_one(sel)
                if el:
                    snippet = el.get_text(" ", strip=True)
                    break

        m = re.search(r"/topic/(\d+)", url) or re.search(r"thread[=/](\d+)", url)
        rid = f"bouwinfo:{m.group(1)}" if m else f"bouwinfo:{url}"

        out.append(RawPost(
            id=rid,
            source="bouwinfo",
            url=url,
            title=title,
            text=snippet,
            metadata={},
        ))
    return out


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    sess = session or PoliteSession(HttpConfig(request_delay=3.0))
    q = f"{query} {location}".strip() if location else query

    seen: set[str] = set()
    out: list[RawPost] = []

    candidate_urls = [
        (f"{BASE}/", {"s": q}),
        (f"{BASE}/index.php", {"app": "core", "module": "search", "do": "search", "search_term": q}),
    ]

    for url, params in candidate_urls:
        if len(out) >= limit:
            break
        resp = sess.get(url, params=params)
        if resp is None:
            continue
        try:
            page_posts = _parse(resp.text)
        except Exception as e:
            log.warning("Bouwinfo parsing fout: %s", e)
            page_posts = []
        for p in page_posts:
            if p.id in seen:
                continue
            seen.add(p.id)
            out.append(p)
            if len(out) >= limit:
                break

    log.info("Bouwinfo: %d posts voor q=%r", len(out), q)
    return out
