"""Consumer lead radar — vindt mensen die actief zoeken naar een installateur.

Bron-onafhankelijke data classes en pipeline-helpers leven hier zodat
sources/, processor/ en output/ los van elkaar staan en testbaar blijven.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
from urllib.parse import urlsplit, urlunsplit
import hashlib


def _canonicalize_url(url: str) -> str:
    """Normalize URL voor dedup-fingerprint.

    - Lowercase scheme + host
    - Strip query-string (utm_*, ?sort=, etc. = view-modifiers, niet content)
    - Strip fragment (#comment-xyz wijst naar pagina-sectie, niet andere post)
    - Strip trailing slash (example.com/x ≡ example.com/x/)

    Resultaat: twee URLs die naar dezelfde resource wijzen krijgen dezelfde
    fingerprint, ook al verschillen ze in tracking-params of view-state.
    """
    if not url:
        return ""
    try:
        parts = urlsplit(url)
    except ValueError:
        return url.lower()
    scheme = (parts.scheme or "").lower()
    netloc = (parts.netloc or "").lower()
    path = parts.path.rstrip("/") if parts.path else ""
    return urlunsplit((scheme, netloc, path, "", ""))


@dataclass
class RawPost:
    """Een ruwe forumpost / listing zoals een source 'm aanlevert."""
    id: str
    source: str
    url: str
    title: str
    text: str
    author: str | None = None
    created_at: str | None = None  # ISO 8601
    metadata: dict[str, Any] = field(default_factory=dict)
    # source_id: granular bron-label voor Sheets (bv. "reddit:r/duurzaam").
    # Default = source (registry name) voor backwards compat.
    source_id: str | None = None

    def __post_init__(self) -> None:
        if self.source_id is None:
            self.source_id = self.source

    def fingerprint(self) -> str:
        """Stable hash voor dedup — source + id + canonical url.

        Canonicalization strips query/fragment/trailing-slash zodat dezelfde
        post met andere view-params (?sort=, utm_*) niet dubbel-tellen.
        """
        key = f"{self.source}|{self.id}|{_canonicalize_url(self.url)}".lower()
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


@dataclass
class Lead:
    """Een gescoorde lead, klaar voor export."""
    id: str
    source: str
    title: str
    text: str
    summary: str
    url: str
    city: str | None
    score: int
    intent: str  # 'hot' | 'warm' | 'cold'
    breakdown: dict[str, Any]
    niche: str
    captured_at: str  # required: ISO-8601 UTC, sourced from RawPost.created_at
    author: str | None = None
    created_at: str | None = None
    source_id: str | None = None

    def __post_init__(self) -> None:
        if self.source_id is None:
            self.source_id = self.source

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        coerced: dict[str, Any] = {}
        for k, v in d["breakdown"].items():
            if isinstance(v, bool):
                coerced[k] = v
            elif isinstance(v, int):
                coerced[k] = v
            elif isinstance(v, float):
                coerced[k] = int(v) if v.is_integer() else v
            else:
                coerced[k] = v
        d["breakdown"] = coerced
        return d


def intent_from_score(score: int) -> str:
    """>=70 hot, 40-69 warm, <40 cold."""
    if score >= 70:
        return "hot"
    if score >= 40:
        return "warm"
    return "cold"


__all__ = ["RawPost", "Lead", "intent_from_score"]
