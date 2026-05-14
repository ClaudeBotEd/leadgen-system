"""Regression-tests voor time-decay in scorer.score_post."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from consumer import RawPost
from consumer.processor.cleaner import clean_post
from consumer.processor.scorer import _time_decay_factor, score_post

NOW = datetime(2026, 5, 14, 12, 0, 0, tzinfo=timezone.utc)


def _iso(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


@pytest.mark.parametrize("days,expected", [
    (0, 1.0),
    (7, 1.0),
    (14, 1.0),
    (15, 0.7),
    (20, 0.7),
    (30, 0.7),
    (31, 0.4),
    (50, 0.4),
    (60, 0.4),
    (61, 0.1),
    (120, 0.1),
])
def test_time_decay_factor_brackets(days: float, expected: float) -> None:
    assert _time_decay_factor(_iso(days), now=NOW) == expected


def test_time_decay_factor_no_timestamp() -> None:
    assert _time_decay_factor(None, now=NOW) == 1.0
    assert _time_decay_factor("", now=NOW) == 1.0


def test_time_decay_factor_invalid_format() -> None:
    assert _time_decay_factor("not-a-date", now=NOW) == 1.0
    assert _time_decay_factor("2026-13-45T99:99:99", now=NOW) == 1.0


def test_time_decay_factor_zulu_format() -> None:
    iso_z = (NOW - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert _time_decay_factor(iso_z, now=NOW) == 0.7


def test_score_with_decay_keeps_fresh_score() -> None:
    raw = RawPost(
        id="x", source="test", url="https://e.x",
        title="CV kapot Utrecht zoek monteur",
        text="Met spoed monteur nodig, geen warm water. Cv-ketel kapot.",
    )
    cleaned = clean_post(raw)
    base_score, base_breakdown = score_post(cleaned, niche_keywords=["cv"])
    decayed_score, decayed_breakdown = score_post(
        cleaned, niche_keywords=["cv"], created_at=_iso(5), now=NOW,
    )
    assert decayed_score == base_score
    assert "time_decay_penalty" not in decayed_breakdown


def test_score_with_decay_halves_after_30d() -> None:
    raw = RawPost(
        id="x", source="test", url="https://e.x",
        title="CV kapot Utrecht zoek monteur",
        text="Met spoed monteur nodig, cv-ketel kapot.",
    )
    cleaned = clean_post(raw)
    base_score, _ = score_post(cleaned, niche_keywords=["cv"])
    decayed_score, decayed_breakdown = score_post(
        cleaned, niche_keywords=["cv"], created_at=_iso(40), now=NOW,
    )
    assert decayed_score < base_score
    assert decayed_breakdown["time_decay_penalty"] < 0
    assert decayed_score == int(round(min(100, base_score) * 0.4))


def test_score_with_decay_caps_old_post() -> None:
    raw = RawPost(
        id="x", source="test", url="https://e.x",
        title="CV kapot Utrecht zoek monteur met spoed",
        text="Met spoed monteur nodig, geen warm water. Cv-ketel kapot. Storing.",
    )
    cleaned = clean_post(raw)
    score, _ = score_post(
        cleaned, niche_keywords=["cv"], created_at=_iso(100), now=NOW,
    )
    assert score == 10
