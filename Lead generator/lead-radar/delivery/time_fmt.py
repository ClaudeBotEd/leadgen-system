"""Relative + absolute time formatting per spec §3.3.

Rules:
- Never say "now" / "just now"; minimum granularity is 1 minute.
- 7 days -> "vorige week"; otherwise N days.
"""

from __future__ import annotations

from datetime import datetime, timezone


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def relative_time(captured: datetime, *, now: datetime) -> str:
    captured = _ensure_utc(captured)
    now = _ensure_utc(now)
    delta = now - captured
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return "1 minuut geleden"
    minutes = total_seconds // 60
    if minutes < 60:
        return "1 minuut geleden" if minutes == 1 else f"{minutes} minuten geleden"
    hours = minutes // 60
    if hours < 24:
        return "1 uur geleden" if hours == 1 else f"{hours} uur geleden"
    days = hours // 24
    if days == 1:
        return "1 dag geleden"
    if days == 7:
        return "vorige week"
    return f"{days} dagen geleden"


def absolute_iso(dt: datetime) -> str:
    dt = _ensure_utc(dt)
    return dt.strftime("%Y-%m-%d %H:%M UTC")
