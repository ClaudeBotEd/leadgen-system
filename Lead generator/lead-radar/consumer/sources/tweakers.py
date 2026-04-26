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


def _parse_search(html: str, query_terms: list[str] | None = None) -> list[RawPost]:
    """Parse Tweakers' /forum/find HTML.

    Tweakers returnt vaak ALLE recente topics ipv te filteren op keyword,
    daarom doen we client-side keyword-filter als query_terms gegeven is.
    """
    soup = BeautifulSoup(html, "html.parser")
    seen_ids: set[str] = set()
    out: list[RawPost] = []

    anchors = soup.select("a[href*='/forum/list_messages']")
    for a in anchors:
        href = a.get("href") or ""
        if not href:
            continue
        url = urljoin(BASE, href)
        title = (a.get_text() or "").strip()
        if not title or title.isdigit() or len(title) < 5:
            continue
        thread_id = _extract_thread_id(href) or url
        rid = f"tweakers:{thread_id}"
        if rid in seen_ids:
            continue
        seen_ids.add(rid)

        if query_terms:
            tl = title.lower()
            if not any(qt.lower() in tl for qt in query_terms):
                continue

        out.append(RawPost(
            id=rid,
            source="tweakers",
            url=url,
            title=title,
            text="",
            author=None,
            created_at=None,
            metadata={},
        ))
    return out


def _set_dpg_consent(sess: PoliteSession) -> None:
    """Tweakers verbergt zoekresultaten achter een DPG Media privacy-gate.
    Met de juiste consent-cookies + 1 warmup-call naar de privacy-gate
    krijgen we volledige HTML."""
    for name, val in [
        ("pwv2-token", "accepted"),
        ("pwv2-consent-tracking-tcfv2", "1"),
        ("cmp_pwv2", "accepted"),
        ("TweakersPrivacyAccepted", "1"),
    ]:
        try:
            sess.session.cookies.set(name, val, domain=".tweakers.net")
        except Exception:
            pass
    # Warmup GET (status mag 400 zijn — zet nog steeds de juiste sessie-cookies)
    try:
        sess.session.get("https://tweakers.net/privacy-gate/store/", timeout=10)
    except Exception:
        pass


def fetch(query: str, *, limit: int = 25, location: str | None = None,
          session: PoliteSession | None = None, **_: object) -> list[RawPost]:
    sess = session or PoliteSession(HttpConfig(request_delay=3.0))
    _set_dpg_consent(sess)
    q = f"{query} {location}".strip() if location else query

    # Splits query in betekenisvolle terms voor client-side filter
    terms = [t for t in re.findall(r"[A-Za-z]{4,}", q) if t.lower() not in {"nederland", "belgie", "belgium"}]
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
            page_posts = _parse_search(resp.text, query_terms=terms or None)
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
