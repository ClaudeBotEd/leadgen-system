"""Reddit public JSON API scraper — voor user discussions over warmtepomp/HVAC.

Gebruikt de publieke `.json` endpoints (geen API key, geen account vereist).
Rate limit: 1 req/sec aanbevolen door Reddit.

Geeft signal data (geen direct leads): subreddits + threads waarin mensen
vragen stellen over warmtepompen — handig om te zien welke termen populair zijn
en eventueel om als 'intent signal' te gebruiken.
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterable

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.rate_limiter import RateLimiter  # noqa: E402


REDDIT_USER_AGENT = "lead-radar:nl-be-hvac:v0.1 (by /u/anonymous)"

DEFAULT_SUBREDDITS = [
    "thenetherlands",
    "Belgium",
    "DutchFIRE",
    "DutchInvestor",
    "duurzaamheid",
    "AskNL",
    "askbe",
    "vlaanderen",
    "Amsterdam",
    "rotterdam",
    "groningen",
    "utrecht",
]

DEFAULT_KEYWORDS = [
    "warmtepomp",
    "hybride warmtepomp",
    "lucht-water",
    "ISDE",
    "aardgasvrij",
    "verwarming vervangen",
    "cv ketel",
    "airco installeren",
    "zonnepanelen offerte",
]


def search(
    keywords: Iterable[str] | None = None,
    subreddits: Iterable[str] | None = None,
    limit: int = 25,
    sort: str = "new",
    time_filter: str = "month",
    rate_limiter: RateLimiter | None = None,
) -> list[dict]:
    """Zoek Reddit op keywords binnen specifieke subreddits.

    Returns list[dict]: {title, url, snippet, subreddit, score, comments, created_utc, source, query}
    """
    keywords = list(keywords or DEFAULT_KEYWORDS)
    subreddits = list(subreddits or DEFAULT_SUBREDDITS)
    limiter = rate_limiter or RateLimiter(min_delay=1.5)

    headers = {"User-Agent": REDDIT_USER_AGENT}
    results: list[dict] = []

    for kw in keywords:
        for sub in subreddits:
            limiter.wait("reddit.com")
            url = (
                f"https://www.reddit.com/r/{sub}/search.json"
                f"?q={requests.utils.quote(kw)}&restrict_sr=on"
                f"&sort={sort}&t={time_filter}&limit={limit}"
            )
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    continue
                data = resp.json()
            except Exception as e:
                print(f"[reddit] fout op r/{sub} '{kw}': {e}")
                continue

            children = data.get("data", {}).get("children", [])
            for child in children:
                d = child.get("data", {})
                if not d.get("title"):
                    continue
                created_utc = d.get("created_utc")
                results.append({
                    "title": d.get("title", ""),
                    "url": "https://www.reddit.com" + d.get("permalink", ""),
                    "snippet": (d.get("selftext", "") or "")[:300],
                    "subreddit": d.get("subreddit", sub),
                    "score": d.get("score", 0),
                    "comments": d.get("num_comments", 0),
                    "created_utc": (
                        datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat(timespec="seconds")
                        if created_utc else ""
                    ),
                    "query": kw,
                    "source": "reddit",
                })
            print(f"[reddit] r/{sub} '{kw}' → {len(children)} threads")

    return results


def find_intent_signals(threads: list[dict]) -> list[dict]:
    """Filter threads die intent signals tonen (mensen die actief naar oplossing zoeken)."""
    intent_words = (
        "offerte", "aanvragen", "installeren", "kosten", "prijs",
        "advies", "aanbeveling", "ervaring", "wie kan", "wie kent",
        "zoek installateur", "installateur gezocht", "tip nodig",
    )
    out = []
    for t in threads:
        text = f"{t.get('title','')} {t.get('snippet','')}".lower()
        matched = [w for w in intent_words if w in text]
        if matched:
            t = dict(t)
            t["intent_words_matched"] = matched
            out.append(t)
    return out


if __name__ == "__main__":
    test = search(keywords=["warmtepomp"], subreddits=["thenetherlands"], limit=5)
    for r in test:
        print(f"- [{r['score']}↑ {r['comments']}💬] {r['title'][:80]}")
    print(f"\nIntent signals: {len(find_intent_signals(test))}")
