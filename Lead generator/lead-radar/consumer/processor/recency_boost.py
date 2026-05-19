"""Recency boost — sharpen scoring on fresh leads.

<24h:   +5
1-7d:   unchanged
7-14d:  -10
>=14d:  AGED_OUT (caller drops the lead entirely)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Final, Union

AGED_OUT: Final = object()
"""Sentinel returned for posts >= 14 days old."""

BOOST_24H = +5
DEMOTE_7D = -10


def apply_recency_boost(
    *,
    score: int,
    created_at: str | None,
    now: datetime | None = None,
) -> Union[int, object]:
    """Return adjusted score, or AGED_OUT if the post is too old to sell."""
    if not created_at:
        return score
    try:
        ts = datetime.fromisoformat(created_at)
    except ValueError:
        return score

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age = now - ts

    if age >= timedelta(days=14):
        return AGED_OUT
    if age >= timedelta(days=7):
        return max(0, min(100, score + DEMOTE_7D))
    if age < timedelta(hours=24):
        return max(0, min(100, score + BOOST_24H))
    return score
