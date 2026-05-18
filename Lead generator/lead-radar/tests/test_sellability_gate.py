"""Sellability gate for HOT-tab admission."""
from __future__ import annotations

from consumer import Lead
from consumer.processor.sellability_gate import is_sellable, GateResult


def _lead(**overrides) -> Lead:
    base = dict(
        id="L1",
        source="reddit",
        source_id="reddit:r/Amsterdam",
        title="t",
        text="b",
        summary="Wie kan een warmtepomp installeren in Amsterdam-Zuid?",
        url="https://reddit.com/r/Amsterdam/post/x",
        city="amsterdam",
        score=82,
        intent="hot",
        breakdown={},
        niche="warmtepomp",
        author="someuser",
        created_at="2026-05-18T09:00:00+02:00",
    )
    base.update(overrides)
    return Lead(**base)


def test_complete_lead_is_sellable():
    result = is_sellable(_lead())
    assert isinstance(result, GateResult)
    assert result.ok is True
    assert result.missing == []


def test_missing_city_blocks():
    result = is_sellable(_lead(city=None))
    assert result.ok is False
    assert "city" in result.missing


def test_short_summary_blocks():
    result = is_sellable(_lead(summary="too short"))
    assert result.ok is False
    assert "summary" in result.missing


def test_truncation_marker_in_summary_blocks():
    result = is_sellable(_lead(summary="something interesting that goes on for a while..."))
    assert result.ok is False
    assert "summary" in result.missing


def test_intent_unknown_blocks():
    result = is_sellable(_lead(intent="unknown"))
    assert result.ok is False
    assert "intent" in result.missing


def test_intent_cold_blocks():
    result = is_sellable(_lead(intent="cold"))
    assert result.ok is False
    assert "intent" in result.missing


def test_missing_author_and_no_author_context_blocks():
    result = is_sellable(_lead(author=None))
    assert result.ok is False
    assert "author" in result.missing


def test_missing_author_with_author_context_in_breakdown_passes():
    """If breakdown has author_context (Reddit author_enrich), missing author is OK."""
    result = is_sellable(_lead(author=None, breakdown={"author_context": "active user, 14 posts on /r/duurzaam"}))
    assert "author" not in result.missing


def test_score_below_80_blocks():
    result = is_sellable(_lead(score=78))
    assert result.ok is False
    assert "score" in result.missing


def test_missing_url_blocks():
    result = is_sellable(_lead(url=""))
    assert result.ok is False
    assert "url" in result.missing


def test_multiple_missing_fields_all_listed():
    result = is_sellable(_lead(city=None, summary="x", intent="cold"))
    assert result.ok is False
    assert {"city", "summary", "intent"}.issubset(set(result.missing))
