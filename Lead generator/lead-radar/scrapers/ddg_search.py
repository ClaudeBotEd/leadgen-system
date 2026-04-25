"""DuckDuckGo search scraper — gratis, geen API key.

Gebruikt de `duckduckgo-search` library (HTML scraping van DDG).
Geen API key, geen account. Respecteert rate limits.

Returns lijst met dicts: {url, title, snippet, source, query}
"""

from __future__ import annotations
import time
from typing import Iterable

try:
    from duckduckgo_search import DDGS
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False

try:
    from utils.rate_limiter import RateLimiter
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from utils.rate_limiter import RateLimiter


def search(
    queries: Iterable[str],
    max_results: int = 30,
    region: str = "nl-nl",
    rate_limiter: RateLimiter | None = None,
    request_delay: float = 2.0,
) -> list[dict]:
    """Run DuckDuckGo search voor een lijst queries.

    Args:
        queries: lijst zoekstrings (bv. ["warmtepomp installateur amsterdam"])
        max_results: max aantal resultaten per query
        region: bv "nl-nl" of "be-nl" of "wt-wt" (worldwide)
        rate_limiter: optionele RateLimiter
        request_delay: fallback delay als rate_limiter None is

    Returns:
        list[dict] met velden: {url, title, snippet, source, query}
    """
    if not DDG_AVAILABLE:
        print("[ddg] duckduckgo-search niet geïnstalleerd. Run: pip install duckduckgo-search")
        return []

    limiter = rate_limiter or RateLimiter(min_delay=request_delay)
    results: list[dict] = []

    with DDGS() as ddgs:
        for query in queries:
            limiter.wait("duckduckgo.com")
            try:
                hits = list(ddgs.text(
                    query,
                    region=region,
                    safesearch="moderate",
                    max_results=max_results,
                ))
            except Exception as e:
                print(f"[ddg] fout bij '{query}': {e}")
                continue

            for hit in hits:
                results.append({
                    "url": hit.get("href") or hit.get("url", ""),
                    "title": hit.get("title", ""),
                    "snippet": hit.get("body", ""),
                    "source": "duckduckgo",
                    "query": query,
                })

            print(f"[ddg] '{query}' → {len(hits)} resultaten")
            time.sleep(0.5)

    return results


def search_dorks(
    site: str,
    keywords: list[str],
    location: str = "",
    max_results: int = 20,
    region: str = "nl-nl",
) -> list[dict]:
    """Google-dork stijl zoekopdrachten op specifieke site.

    Voorbeeld:
        search_dorks("linkedin.com/in", ["warmtepomp installateur"], "amsterdam")
    """
    queries = [f'site:{site} "{kw}" {location}'.strip() for kw in keywords]
    return search(queries, max_results=max_results, region=region)


if __name__ == "__main__":
    test_results = search(
        queries=["warmtepomp installateur amsterdam"],
        max_results=5,
    )
    for r in test_results:
        print(f"- {r['title'][:60]} → {r['url']}")
