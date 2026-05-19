"""Recency boost — explicit score adjustment based on post age."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from consumer.processor.recency_boost import apply_recency_boost, AGED_OUT


NOW = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)


def _age(hours: float) -> str:
    return (NOW - timedelta(hours=hours)).isoformat(timespec="seconds")


def test_post_under_24h_gets_plus_5():
    assert apply_recency_boost(score=70, created_at=_age(12), now=NOW) == 75


def test_post_at_24h_boundary_no_boost():
    assert apply_recency_boost(score=70, created_at=_age(24), now=NOW) == 70


def test_post_3d_old_unchanged():
    assert apply_recency_boost(score=70, created_at=_age(72), now=NOW) == 70


def test_post_at_7d_boundary_gets_minus_10():
    assert apply_recency_boost(score=70, created_at=_age(7 * 24), now=NOW) == 60


def test_post_10d_old_gets_minus_10():
    assert apply_recency_boost(score=70, created_at=_age(240), now=NOW) == 60


def test_post_older_than_14d_returns_aged_out_marker():
    assert apply_recency_boost(score=70, created_at=_age(15 * 24), now=NOW) is AGED_OUT


def test_post_at_14d_boundary_returns_aged_out():
    assert apply_recency_boost(score=70, created_at=_age(14 * 24), now=NOW) is AGED_OUT


def test_missing_created_at_passes_through_unchanged():
    assert apply_recency_boost(score=70, created_at=None, now=NOW) == 70


def test_malformed_created_at_passes_through():
    assert apply_recency_boost(score=70, created_at="not-a-date", now=NOW) == 70


def test_score_with_boost_clamped_to_100():
    assert apply_recency_boost(score=98, created_at=_age(12), now=NOW) == 100


def test_naive_datetime_in_created_at_treated_as_utc():
    """ISO without tz offset should be parsed as UTC, not crash."""
    naive_iso = (NOW.replace(tzinfo=None) - timedelta(hours=12)).isoformat(timespec="seconds")
    assert apply_recency_boost(score=70, created_at=naive_iso, now=NOW) == 75
