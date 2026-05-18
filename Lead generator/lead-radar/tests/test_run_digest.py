"""Run-digest formatter for end-of-run Telegram messages."""
from __future__ import annotations

from consumer.output.telegram import format_run_digest, RunStats, SourceStat


def test_digest_has_header_with_timestamp():
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            SourceStat(source="marktplaats", posts=42, leads=8, hot=3, dead=False),
        ],
        apify_spend_used_usd=1.85,
        apify_spend_cap_usd=5.00,
    )
    msg = format_run_digest(stats)
    assert "2026-05-18" in msg
    assert "13:00" in msg


def test_digest_marks_dead_source_with_x():
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            SourceStat(source="bouwinfo", posts=0, leads=0, hot=0, dead=True),
        ],
        apify_spend_used_usd=0,
        apify_spend_cap_usd=5.00,
    )
    msg = format_run_digest(stats)
    assert "✗" in msg
    assert "bouwinfo" in msg
    assert "DEAD" in msg


def test_digest_marks_alive_source_with_check():
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            SourceStat(source="reddit", posts=12, leads=2, hot=1, dead=False),
        ],
        apify_spend_used_usd=0,
        apify_spend_cap_usd=5.00,
    )
    msg = format_run_digest(stats)
    assert "✓" in msg
    assert "reddit" in msg


def test_digest_totals_aggregate():
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            SourceStat(source="marktplaats", posts=42, leads=8, hot=3, dead=False),
            SourceStat(source="reddit_new", posts=87, leads=6, hot=1, dead=False),
            SourceStat(source="bouwinfo", posts=0, leads=0, hot=0, dead=True),
        ],
        apify_spend_used_usd=1.85,
        apify_spend_cap_usd=5.00,
    )
    msg = format_run_digest(stats)
    assert "Total: 14 leads" in msg
    assert "4 HOT" in msg


def test_digest_shows_apify_spend():
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[],
        apify_spend_used_usd=3.24,
        apify_spend_cap_usd=5.00,
    )
    msg = format_run_digest(stats)
    assert "$3.24" in msg
    assert "$5.00" in msg


def test_digest_dead_sources_sorted_last():
    """In the rendered output, dead sources appear after alive ones."""
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            SourceStat(source="dead_one", posts=0, leads=0, hot=0, dead=True),
            SourceStat(source="alive_one", posts=10, leads=2, hot=1, dead=False),
        ],
        apify_spend_used_usd=0,
        apify_spend_cap_usd=0,
    )
    msg = format_run_digest(stats)
    alive_idx = msg.index("alive_one")
    dead_idx = msg.index("dead_one")
    assert alive_idx < dead_idx, "dead sources must render after alive ones"


def test_digest_omits_apify_line_when_cap_zero():
    """If no Apify cap configured, don't show the spend line."""
    stats = RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            SourceStat(source="reddit", posts=12, leads=2, hot=1, dead=False),
        ],
        apify_spend_used_usd=0,
        apify_spend_cap_usd=0,
    )
    msg = format_run_digest(stats)
    assert "Apify spend" not in msg
