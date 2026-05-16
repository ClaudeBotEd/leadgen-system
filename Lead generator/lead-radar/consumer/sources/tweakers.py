"""Tweakers Gathering of Tomorrow forum source.

Tweakers heeft geen publieke API.  We gebruiken hun Algemene Zoeken-pagina:
  https://gathering.tweakers.net/forum/find?keywords=...

Antwoorden zijn HTML — we parsen met BeautifulSoup.  Bij wijzigingen aan de
HTML structuur faalt parsing maar returnen we []  — geen crash.

Anti-bot workaround (2026-05-15): Tweakers/DPG Media privacy-gate
detecteert PoliteSession's rijke Accept/Accept-Language/Accept-Encoding
headers als 'unusual client' en redirect naar consent-gate ondanks
geldige cookies (8KB gate HTML ipv 400KB resultaten).  De search-call
gebruikt daarom `lean_headers=True` (PoliteSession-feature) waardoor
sessie-level headers gestript worden — alleen User-Agent + Cookie blijft.
Cookies worden vooraf gezet door _set_dpg_consent.
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

# Hoe diep we per query crawlen.  Tweakers's interne search filtert
# matig — diepere pages bevatten oudere threads die de keyword nog
# steeds matchen via client-side filter (_parse_search query_terms).
# 5 = vergroting van 3 (default vóór 2026-05-14 expansie).
MAX_SEARCH_PAGES = 5


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
    krijgen we volledige HTML.

    Cached per-sessie via `_dpg_consent_done` attribuut: cookies blijven
    geldig zolang de session bestaat, dus 1 warmup-call volstaat.  Bij
    1380 fetch()-aanroepen op zelfde sessie scheelt dit 1379 nutteloze
    extra HTTP-calls.
    """
    if getattr(sess, "_dpg_consent_done", False):
        return
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
    try:
        sess._dpg_consent_done = True  # type: ignore[attr-defined]
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
    for page in range(1, MAX_SEARCH_PAGES + 1):
        if len(out) >= limit:
            break
        params = {"keywords": q, "page": page}
        # lean_headers=True — Tweakers/DPG anti-bot redirect naar consent-gate
        # bij rijke Accept/Accept-Language headers ondanks geldige cookies.
        # Zie module docstring KNOWN ISSUE 2026-05-15.
        resp = sess.get(SEARCH_URL, params=params, lean_headers=True)
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

    if not deduped:
        deduped = _google_site_fallback(q, limit)

    log.info("Tweakers: %d posts voor q=%r", len(deduped), q)
    return deduped


def _google_site_fallback(q: str, limit: int) -> list[RawPost]:
    """Tweakers' eigen /forum/find filtert niet meer op keyword (KNOWN ISSUE).
    Bij 0 directe hits vragen we Google via site:gathering.tweakers.net.
    Posts blijven herkenbaar als source='tweakers' voor downstream filters.
    """
    try:
        from . import google as _g
    except Exception:
        return []
    try:
        results = _g.fetch(f"site:gathering.tweakers.net {q}", limit=limit)
    except Exception as e:
        log.warning("Tweakers Google-fallback faalde: %s", e)
        return []
    rebadged: list[RawPost] = []
    for p in results:
        thread_id = _extract_thread_id(p.url) or p.url
        rebadged.append(RawPost(
            id=f"tweakers:{thread_id}",
            source="tweakers",
            url=p.url,
            title=p.title,
            text=p.text,
            author=p.author,
            created_at=p.created_at,
            metadata={**(p.metadata or {}), "via": "google_site_fallback"},
        ))
    return rebadged
