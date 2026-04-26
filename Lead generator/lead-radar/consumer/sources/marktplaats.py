"""Marktplaats source — alleen publieke listings, geen login.

Gebruikt de publieke search-URL `/q/<query>/`.  Listings worden vaak
geinjecteerd via een ingebed JSON blob (window.__CONFIG__ / __INITIAL_DATA__)
— we proberen dat eerst, met BS4-fallback op de HTML cards.

Wordt ook hergebruikt door 2dehands.be (zelfde codebase, andere BASE).
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


def _parse_html(html: str, base: str, source_name: str) -> list[RawPost]:
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
            url = urljoin(base, vip_url) if vip_url else base
            cat = (li.get("categorySpecificFields") or {}).get("categoryName") or ""
            seller_type = (li.get("sellerInformation") or {}).get("sellerName") or ""
            if not ad_id or not title:
                continue
            out.append(RawPost(
                id=f"{source_name}:{ad_id}",
                source=source_name,
                url=url,
                title=title,
                text=desc,
                metadata={"category": cat, "seller": seller_type},
            ))
        if out:
            return out

    for li in soup.select("li.hz-Listing, li.mp-Listing, article.search-result"):
        link = li.select_one("a[href*='/v/'], a.mp-Listing-coverLink, a.hz-Listing-coverLink")
        if not link:
            continue
        href = link.get("href") or ""
        url = urljoin(base, href)
        title_el = li.select_one("h3, .mp-Listing-title, .hz-Listing-title")
        title = title_el.get_text(strip=True) if title_el else (link.get_text(strip=True) or "")
        desc_el = li.select_one(".mp-Listing-description, .hz-Listing-description, p")
        desc = desc_el.get_text(" ", strip=True) if desc_el else ""
        m = re.search(r"/v/[^/]+/[^/]+/([\w-]+)", href)
        ad_id = m.group(1) if m else href
        if not title:
            continue
        out.append(RawPost(
            id=f"{source_name}:{ad_id}",
            source=source_name,
            url=url,
            title=title,
            text=desc,
            metadata={},
        ))
    return out


def fetch_classifieds(
    base: str,
    query: str,
    *,
    source_name: str,
    limit: int = 25,
    location: str | None = None,
    session: PoliteSession | None = None,
) -> list[RawPost]:
    """Generieke fetcher voor marktplaats.nl en 2dehands.be — zelfde JSON/HTML."""
    sess = session or PoliteSession(HttpConfig(request_delay=2.5))
    q = f"{query} {location}".strip() if location else query

    # Search-URL.  Sorteer op datum (recent eerst) voor verse leads.
    out: list[RawPost] = []
    seen: set[str] = set()
    for variant in (q, f"{q} gezocht", f"{q} gevraagd"):
        if len(out) >= limit:
            break
        url = f"{base}/q/{quote(variant)}/"
        resp = sess.get(url)
        if resp is None:
            continue
        try:
            page = _parse_html(resp.text, base=base, source_name=source_name)
        except Exception as e:
            log.warning("%s parsing fout (q=%r): %s", source_name, variant, e)
            page = []
        for p in page:
            if p.id in seen:
                continue
            seen.add(p.id)
            out.append(p)
            if len(out) >= limit:
                break

    log.info("%s: %d listings voor q=%r", source_name, len(out), q)
    return out[:limit]


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    return fetch_classifieds(
        BASE, query, source_name="marktplaats",
        limit=limit, location=location, session=session,
    )
