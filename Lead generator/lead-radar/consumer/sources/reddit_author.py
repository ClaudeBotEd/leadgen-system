"""Reddit author-enrichment — fetcht publieke profielinfo om recurring
askers/researchers te detecteren.

Voor elke Reddit-lead willen we weten:
- Hoe oud is dit account?
- Hoeveel renovatie-niche-posts heeft de gebruiker recent gemaakt?
- Is dit een "recurring asker" (>=5 posts in renovatie-subs in 90d)?

Recurring askers zijn meestal researchers / forum-vaste klanten, niet
echte buyers.  We willen ze met -20 penalty doorlatend houden maar
deprioriteren in de top-leads.

Cache TTL 24h per (lowercase) auteur, JSON-file in cache_dir.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

DEFAULT_CACHE_TTL_S = 24 * 3600
DEFAULT_TIMEOUT_S = 8
USER_AGENT = "lead-radar/0.2 (consumer-quality)"

RENOVATION_SUBS: frozenset[str] = frozenset({
    "thenetherlands", "bouwen", "kassa", "renovatie",
    "warmtepompen", "heatpumps", "hvac", "duurzaam", "tweakers",
    "vragenenmeer", "diy", "wonen", "huizenmarkt", "energiezuinigwonen",
})


@dataclass
class AuthorProfile:
    author: str
    available: bool
    submission_count: int = 0
    comment_count: int = 0
    renovation_subs_hit: tuple[str, ...] = ()
    total_score: int = 0
    account_age_days: int | None = None
    is_recurring_asker: bool = False
    error: str | None = None
    fetched_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["renovation_subs_hit"] = list(d["renovation_subs_hit"])
        return d

    @property
    def signal_penalty(self) -> int:
        """Score-aanpassing: recurring askers krijgen -20.  Anders 0."""
        return -20 if self.is_recurring_asker else 0


def _unavailable(author: str, reason: str) -> AuthorProfile:
    return AuthorProfile(author=author, available=False, error=reason)


def _cache_path(cache_dir: Path, author: str) -> Path:
    h = hashlib.sha1(author.lower().encode("utf-8")).hexdigest()[:16]
    return cache_dir / f"{h}.json"


def _cache_load(path: Path, ttl_s: int) -> AuthorProfile | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        fetched = raw.get("fetched_at")
        if fetched:
            dt = datetime.fromisoformat(fetched.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - dt).total_seconds() > ttl_s:
                return None
        raw["renovation_subs_hit"] = tuple(raw.get("renovation_subs_hit", []))
        return AuthorProfile(**raw)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
        log.debug("author cache miss: %s", e)
        return None


def _cache_save(path: Path, profile: AuthorProfile) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile.to_dict(), ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        log.debug("author cache write failed: %s", e)


def _fetch_reddit_user(author: str, timeout_s: int) -> dict | None:
    """Fetcht publieke Reddit-user JSON.  None bij fout/404."""
    url = f"https://www.reddit.com/user/{author}/.json?limit=50"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout_s)
    except requests.RequestException as e:
        log.debug("reddit user fetch failed: %s", e)
        return None
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        log.debug("reddit user non-200: %d", resp.status_code)
        return None
    try:
        return resp.json()
    except ValueError:
        return None


def _parse_user_payload(author: str, payload: dict) -> AuthorProfile:
    children = (payload.get("data") or {}).get("children") or []
    submissions = 0
    comments = 0
    total_score = 0
    subs_hit: set[str] = set()
    earliest_created: float | None = None

    for child in children:
        kind = child.get("kind")
        data = child.get("data") or {}
        sub = (data.get("subreddit") or "").lower()
        if kind == "t3":
            submissions += 1
        elif kind == "t1":
            comments += 1
        try:
            score = int(data.get("score") or 0)
            total_score += score
        except (TypeError, ValueError):
            pass
        if sub in RENOVATION_SUBS:
            subs_hit.add(sub)
        ts = data.get("created_utc")
        if isinstance(ts, (int, float)):
            earliest_created = ts if earliest_created is None else min(earliest_created, ts)

    age_days: int | None = None
    if earliest_created is not None:
        age_seconds = time.time() - earliest_created
        age_days = max(0, int(age_seconds / 86400))

    is_recurring = (submissions + comments) >= 5 and len(subs_hit) >= 1

    return AuthorProfile(
        author=author,
        available=True,
        submission_count=submissions,
        comment_count=comments,
        renovation_subs_hit=tuple(sorted(subs_hit)),
        total_score=total_score,
        account_age_days=age_days,
        is_recurring_asker=is_recurring,
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def enrich_author(
    author: str | None,
    *,
    cache_dir: Path | None = None,
    cache_ttl_s: int = DEFAULT_CACHE_TTL_S,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    fetch_fn=None,
) -> AuthorProfile:
    """Fetch & cache author info.  `fetch_fn` is voor testbaarheid.

    Bij ontbrekende author / network-fout / 404: returns een
    `available=False` profile met empty fields — caller blijft zonder
    crash en kan zelf besluiten geen penalty toe te passen.
    """
    if not author or author in ("[deleted]", "deleted", "AutoModerator"):
        return _unavailable(author or "", "missing_or_deleted")

    if cache_dir:
        cache_path = _cache_path(cache_dir, author)
        cached = _cache_load(cache_path, cache_ttl_s)
        if cached is not None:
            return cached

    fetcher = fetch_fn or _fetch_reddit_user
    payload = fetcher(author, timeout_s)
    if not payload:
        return _unavailable(author, "fetch_failed_or_404")

    profile = _parse_user_payload(author, payload)
    if cache_dir:
        _cache_save(_cache_path(cache_dir, author), profile)
    return profile


__all__ = [
    "DEFAULT_CACHE_TTL_S", "RENOVATION_SUBS",
    "AuthorProfile",
    "enrich_author",
]
