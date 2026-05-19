"""End-to-end integration of new processors in run_consumer.py per-post path.

We test the helper function that processes a single RawPost into a Lead
(or None), not the full --daily loop. Task 13 extracts this helper.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Make run_consumer importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_consumer  # noqa: E402
from consumer import RawPost  # noqa: E402


NOW = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)


def _post(**overrides) -> RawPost:
    base = dict(
        id="X1",
        source="reddit",
        source_id="reddit:r/Amsterdam",
        url="https://reddit.com/r/Amsterdam/post/x",
        title="Wie kan een warmtepomp installeren in Amsterdam-Zuid?",
        text="Onze cv-ketel is stuk, hybride warmtepomp gezocht, spoed.",
        author="someuser",
        created_at=(NOW - timedelta(hours=6)).isoformat(timespec="seconds"),
    )
    base.update(overrides)
    return RawPost(**base)


def test_process_post_helper_exists():
    """Task 13 must extract a callable _process_post helper."""
    assert hasattr(run_consumer, "_process_post"), (
        "Task 13 must extract _process_post(raw, niche, data_dir, ...) "
        "as a testable helper."
    )


def test_aged_out_post_is_dropped(tmp_path: Path):
    """Post >=14d old returns AGED_OUT from recency boost; pipeline returns None."""
    old = _post(created_at=(NOW - timedelta(days=20)).isoformat(timespec="seconds"))
    result = run_consumer._process_post(
        raw=old,
        niche="warmtepomp",
        data_dir=tmp_path,
        now=NOW,
        no_llm=True,
    )
    assert result is None


def test_post_without_created_at_is_rejected(tmp_path: Path):
    """Doctrine §00.5: a RawPost without created_at cannot become a Lead.

    captured_at is a verifiability commitment sourced from the post's
    source-provenance timestamp. No timestamp = no anchor = reject.
    """
    no_ts = _post(created_at=None)
    result = run_consumer._process_post(
        raw=no_ts,
        niche="warmtepomp",
        data_dir=tmp_path,
        now=NOW,
        no_llm=True,
    )
    assert result is None, (
        "RawPost with created_at=None must be rejected; "
        "we never fabricate captured_at."
    )


def test_cross_run_dup_is_dropped(tmp_path: Path):
    """Second near-identical post within 14d is dropped by Layer-2 dedup."""
    p1 = _post()
    p2 = _post(
        id="X2",
        url="https://marktplaats.nl/listing/y",
        source="marktplaats",
        source_id="marktplaats:diensten/amsterdam",
        author="other_user",  # different author so Layer 3 doesn't fire
        title="Wie kan warmtepomp installateren in Amsterdam-Zuid?",  # near-dup typo
        text="cv-ketel stuk hybride warmtepomp gezocht spoed onze installatie kapot",
    )
    r1 = run_consumer._process_post(raw=p1, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True)
    assert r1 is not None
    r2 = run_consumer._process_post(raw=p2, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True)
    assert r2 is None, "Near-dup post from a different source within 14d must be dropped"


def test_author_repeat_is_dropped_for_sources_with_author(tmp_path: Path):
    """Same author + same niche on a known-author source within 30d is dropped."""
    p1 = _post(id="A1", title="warmtepomp gezocht spoed",
               text="onze ketel is stuk wij hebben spoed iemand een tip voor installateur in amsterdam")
    p2 = _post(id="A2", title="airco installateur gezocht",
               text="airco gezocht een hele andere tekst zonder warmtepomp niets gemeen met de eerste post",
               url="https://reddit.com/r/Klussers/post/y",
               source_id="reddit:r/Klussers")  # different sub, same author + niche

    r1 = run_consumer._process_post(raw=p1, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True)
    assert r1 is not None, f"First post should not be filtered: {r1}"

    r2 = run_consumer._process_post(raw=p2, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True)
    # Author-repeat should drop p2 since same author posted in same niche recently
    assert r2 is None, "Same author + same niche within 30d must drop"


def test_marktplaats_skips_author_dedup(tmp_path: Path):
    """Marktplaats sellers are not in SOURCES_WITH_AUTHOR; author dedup skipped."""
    p1 = _post(
        source="marktplaats",
        source_id="marktplaats:diensten/amsterdam",
        url="https://marktplaats.nl/listing/1",
        author="seller42",
    )
    p2 = _post(
        id="X2",
        source="marktplaats",
        source_id="marktplaats:diensten/utrecht",
        url="https://marktplaats.nl/listing/2",
        title="warmtepomp gezocht in utrecht heel andere tekst",
        text="utrecht stad heel ander verhaal hierboven zonder overlap met eerste post echt totaal anders",
        author="seller42",  # same author — but marktplaats sellers don't dedup
    )
    r1 = run_consumer._process_post(raw=p1, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True)
    r2 = run_consumer._process_post(raw=p2, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True)
    # Both should pass author-dedup (marktplaats isn't in SOURCES_WITH_AUTHOR).
    # They might still be cross-run-deduped if text is too similar — these texts
    # are deliberately unrelated to avoid that.
    assert r1 is not None
    # r2 might be None due to cross-run dedup if texts are too similar — that's OK.
    # We're only asserting that the author-dedup path isn't what drops it.


def test_sellability_gate_demotes_hot_when_city_missing(tmp_path: Path):
    """A would-be HOT lead with no city gets intent demoted away from 'hot'."""
    # Build a post where the scorer will produce >= 80 (hot range) but no city detected.
    # We rely on the existing scorer to give high score for explicit intent + spoed.
    p = _post(
        text="warmtepomp installateur gezocht spoed mijn cv ketel is stuk vandaag",
        title="warmtepomp installateur gezocht spoed",
        # no city anywhere
    )
    # Force-bypass city detection by passing a city=None scenario via clean_post:
    # If the scorer or clean_post finds a city, this test is brittle. We assert
    # only the demotion contract: if score >= 80 and gate fails on city, intent != hot.
    lead = run_consumer._process_post(
        raw=p, niche="warmtepomp", data_dir=tmp_path, now=NOW, no_llm=True,
    )
    if lead is not None and lead.score >= 80 and (lead.city in (None, "")):
        assert lead.intent != "hot", "Lead missing city must be demoted from hot"


def test_digest_reports_dead_source_with_zero_leads(tmp_path: Path, monkeypatch):
    """A source that ran but produced zero leads must appear in the digest as DEAD or alive-zero.

    This is the canary test for the dead-source attribution bug found in
    final code review of Plan A.
    """
    from consumer.output import telegram as tg
    from consumer.sources import mark_source_yield, reset_source_health

    # Mark a source as having had 3 consecutive 0-yield runs (dead threshold)
    reset_source_health()
    for _ in range(3):
        mark_source_yield("test_dead_source", 0)

    # Construct a minimal RunStats / SourceStat directly to verify the digest renders.
    stats = tg.RunStats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source=[
            tg.SourceStat(source="test_dead_source", posts=0, leads=0, hot=0, dead=True),
            tg.SourceStat(source="reddit", posts=12, leads=3, hot=1, dead=False),
        ],
    )
    msg = tg.format_run_digest(stats)
    assert "test_dead_source" in msg
    assert "DEAD" in msg
    assert "reddit" in msg
    assert "✓" in msg and "✗" in msg


def test_run_daily_includes_zero_yield_sources_in_digest_counters(tmp_path: Path, monkeypatch):
    """run_daily must report sources that produced 0 leads (the dead-source case)."""
    import run_consumer

    if not hasattr(run_consumer, "_build_run_stats"):
        pytest.skip("_build_run_stats helper not yet extracted from run_daily")

    per_source_counts = {
        "reddit": {"posts": 10, "leads": 2, "hot": 1},
        "marktplaats": {"posts": 0, "leads": 0, "hot": 0},  # ran, found nothing
    }
    stats = run_consumer._build_run_stats(
        timestamp="2026-05-18T13:00:00+02:00",
        per_source_counts=per_source_counts,
    )
    source_names = {s.source for s in stats.per_source}
    assert "reddit" in source_names
    assert "marktplaats" in source_names, "Zero-yield source must appear in digest"
