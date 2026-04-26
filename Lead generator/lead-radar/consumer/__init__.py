"""Consumer lead radar — vindt mensen die actief zoeken naar een installateur.

Bron-onafhankelijke data classes en pipeline-helpers leven hier zodat
sources/, processor/ en output/ los van elkaar staan en testbaar blijven.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
import hashlib


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

    def fingerprint(self) -> str:
        """Stable hash voor dedup — combineert source + id + url."""
        key = f"{self.source}|{self.id}|{self.url}".lower()
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
    breakdown: dict[str, int]
    niche: str
    author: str | None = None
    created_at: str | None = None
    captured_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["breakdown"] = {k: int(v) for k, v in d["breakdown"].items()}
        return d


def intent_from_score(score: int) -> str:
    """>=70 hot, 40-69 warm, <40 cold."""
    if score >= 70:
        return "hot"
    if score >= 40:
        return "warm"
    return "cold"


__all__ = ["RawPost", "Lead", "intent_from_score"]
