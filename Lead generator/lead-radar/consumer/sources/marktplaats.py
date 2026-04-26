"""Marktplaats source — alleen publieke listings, geen login.

Gebruikt de publieke search-URL `/q/<query>/`.  Listings worden vaak
geinjecteerd via een ingebed JSON blob (window.__CONFIG__ / __INITIAL_DATA__)
— we proberen dat eerst, met BS4-fallback op de HTML cards.

Note: Marktplaats listings zijn vooral 'aangeboden' — om vraag-listings te
vinden helpen queries met 'gezocht' of 'monteur gezocht'.
"""
from __future__ import annotations

import json
import logging
import re
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from .. import RawPost
from ..utils import PoliteSession, HttpConfig

log = logging.getLogger("consumer.sources.marktplaats")

BASE = "https://www.marktplaats.nl"


def _parse_html(html: str) -> list[RawPost]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[RawPost] = []

    for script in soup.find_all("script"):
        text = script.string or ""
        if not text or ("__CONFIG__" not in text and "__INITIAL_DATA__" not in text and "listings" not in text):
            continue
        m = re.search(r'"listings"\s*:\s*(\[.*?\])\s*,\s*"', text, re.DOTALL)
        if not m:
            continue
        try:
            listings = json.loads(m.group(1))
        except Exception:
            continue
        for li in listings:
            if not isinstance(li, dict):
                continue
            ad_id = li.get("itemId") or li.get("id") or ""
            title = li.get("title") or ""
            desc = li.get("description") or ""
            vip_url = li.get("vipUrl") or ""
            url = urljoin(BASE, vip_url) if vip_url else BASE
            cat = (li.get("categorySpecificFields") or {}).get("categoryName") or ""
            if not ad_id or not title:
                continue
            out.append(RawPost(
                id=f"marktplaats:{ad_id}",
                source="marktplaats",
                url=url,
                title=title,
                text=desc,
                metadata={"category": cat},
            ))
        if out:
            return out

    for li in soup.select("li.hz-Listing, li.mp-Listing, article.search-result"):
        link = li.select_one("a[href*='/v/'], a.mp-Listing-coverLink, a.hz-Listing-coverLink")
        if not link:
            continue
        href = link.get("href") or ""
        url = urljoin(BASE, href)
        title_el = li.select_one("h3, .mp-Listing-title, .hz-Listing-title")
        title = title_el.get_text(strip=True) if title_el else (link.get_text(strip=True) or "")
        desc_el = li.select_one(".mp-Listing-description, .hz-Listing-description, p")
        desc = desc_el.get_text(" ", strip=True) if desc_el else ""
        m = re.search(r"/v/[^/]+/[^/]+/([\w-]+)", href)
        ad_id = m.group(1) if m else href
        if not title:
            continue
        out.append(RawPost(
            id=f"marktplaats:{ad_id}",
            source="marktplaats",
            url=url,
            title=title,
            text=desc,
            metadata={},
        ))
    return out


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    sess = session or PoliteSession(HttpConfig(request_delay=3.0))
    q = f"{query} {location}".strip() if location else query

    url = f"{BASE}/q/{quote(q)}/"
    resp = sess.get(url)
    if resp is None:
        return []
    try:
        out = _parse_html(resp.text)
    except Exception as e:
        log.warning("Marktplaats parsing fout: %s", e)
        out = []

    out = out[:limit]
    log.info("Marktplaats: %d listings voor q=%r", len(out), q)
    return out
