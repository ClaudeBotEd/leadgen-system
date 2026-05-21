"""Decay window check per doctrine 01.6.

A captured signal is `decayed` when its age exceeds the configured
window (default 8 days). Decay does NOT prevent delivery; it tells
the renderer to add a DECAYED pill and (if archive_url is present)
swap the source link.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

DEFAULT_DECAY_DAYS = 8


def is_decayed(captured: datetime, *, now: datetime, decay_days: int = DEFAULT_DECAY_DAYS) -> bool:
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - captured) >= timedelta(days=decay_days)
