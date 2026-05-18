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
        captured_at="2026-05-18T09:00:00+02:00",
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
    """A summary that contains 'read more' or 'see full post' mid-text indicates source-side truncation."""
    result = is_sellable(_lead(summary="Wie kan warmtepomp installeren read more in Amsterdam"))
    assert result.ok is False
    assert "summary" in result.missing


def test_summary_ending_with_ellipsis_from_make_summary_is_sellable():
    """make_summary appends trailing '…' on auto-summarized text. That's fine."""
    long_summary = "Wie kan een warmtepomp installeren in Amsterdam-Zuid spoed nodig…"
    result = is_sellable(_lead(summary=long_summary))
    assert result.ok is True, f"Trailing … from make_summary should not block: {result.missing}"


def test_summary_ending_with_three_dots_from_make_summary_is_sellable():
    long_summary = "Wie kan een warmtepomp installeren in Amsterdam-Zuid spoed nodig..."
    result = is_sellable(_lead(summary=long_summary))
    assert result.ok is True


def test_mid_text_truncation_still_blocks():
    """If 'see full post' or 'read more' is INSIDE the summary, that's a real signal."""
    bad_summary = "Wie zoekt een warmtepomp installateur in see full post Amsterdam-Zuid"
    result = is_sellable(_lead(summary=bad_summary))
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
