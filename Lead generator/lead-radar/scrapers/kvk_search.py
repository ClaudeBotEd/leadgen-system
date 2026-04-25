"""KVK / KBO public business search — Dutch & Belgian Chamber of Commerce.

Beide kamers van koophandel hebben een publieke zoekfunctie. KVK heeft ook een
gratis API (met registratie), maar deze module gebruikt ALLEEN publieke
endpoints — geen account vereist.

NOTE: Deze scraper geeft je company NAMES + KVK/KBO numbers + plaats. Voor
website + email moet je de naam dan via DDG zoeken (zie ddg_search.py).

KVK gebruikt JavaScript-rendering wat scrapen complex maakt. Daarom gebruiken
we hier de openbare zoek via DDG dorks.

Gebruik:
    from scrapers.kvk_search import search_open_data
    leads = search_open_data(sbi_codes=["4322"], cities=["amsterdam"])
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Iterable

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.rate_limiter import RateLimiter  # noqa: E402


KVK_BASE = "https://www.kvk.nl"
KBO_BASE = "https://kbopub.economie.fgov.be/kbopub"


def search_via_ddg(
    sbi_codes: Iterable[str] = ("4322",),
    cities: Iterable[str] = ("amsterdam",),
    keywords: Iterable[str] | None = None,
    max_results: int = 20,
) -> list[dict]:
    """Zoek bedrijven via DDG met site:kvk.nl filter."""
    try:
        from .ddg_search import search as ddg_search
    except ImportError:
        from scrapers.ddg_search import search as ddg_search

    queries = []
    keyword_list = list(keywords or ["warmtepomp", "installateur", "klimaattechniek"])

    for kw in keyword_list:
        for city in cities:
            queries.append(f'site:kvk.nl "{kw}" {city}')

    return ddg_search(queries, max_results=max_results)


def lookup_kvk_number(kvk_number: str, rate_limiter: RateLimiter | None = None) -> dict:
    """Lookup een KVK nummer via publieke zoekURL."""
    limiter = rate_limiter or RateLimiter(min_delay=2.0)
    limiter.wait("kvk.nl")
    url = f"{KVK_BASE}/zoeken/?source=all&q={kvk_number}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; lead-radar/0.1)"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        return {
            "kvk_number": kvk_number,
            "status_code": resp.status_code,
            "url": url,
            "html_length": len(resp.text),
        }
    except Exception as e:
        return {"kvk_number": kvk_number, "error": str(e)}


def lookup_kbo_number(kbo_number: str, rate_limiter: RateLimiter | None = None) -> dict:
    """Lookup een KBO/BCE nummer via publieke ondernemingsdatabank (BE)."""
    limiter = rate_limiter or RateLimiter(min_delay=2.0)
    limiter.wait("kbopub.economie.fgov.be")
    cleaned = kbo_number.replace(".", "").replace(" ", "").lstrip("0")
    url = f"{KBO_BASE}/zoeknummerform.html?nummer={cleaned}&actionLu=Zoek"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; lead-radar/0.1)"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        return {
            "kbo_number": kbo_number,
            "status_code": resp.status_code,
            "url": url,
            "html_length": len(resp.text),
        }
    except Exception as e:
        return {"kbo_number": kbo_number, "error": str(e)}


def search_open_data(
    sbi_codes: Iterable[str] = ("4322", "4329"),
    cities: Iterable[str] | None = None,
    keywords: Iterable[str] | None = None,
    max_results: int = 30,
) -> list[dict]:
    """Hoofdfunctie — wrapper rond search_via_ddg met sensible defaults."""
    cities = list(cities or ["amsterdam", "rotterdam", "utrecht"])
    return search_via_ddg(
        sbi_codes=sbi_codes,
        cities=cities,
        keywords=keywords,
        max_results=max_results,
    )


if __name__ == "__main__":
    results = search_open_data(cities=["amsterdam"], max_results=5)
    for r in results:
        print(f"- {r['title'][:80]} → {r['url']}")
