"""Operator-paste-time captured_at is doctrinally valid (§00.4 carve-out).

Doctrine §00.5 forbids fabricating captured_at — a scraper auto-filling
``datetime.now()`` to paper over a missing source timestamp is a lie about
provenance. BUT when an operator manually pastes content into
``analyze_manual_posts(...)``, the operator vouches for the paste moment as
the legitimate signal-observation time (§00.4: humans accountable). The
operator IS the human trail. Paste-time IS the captured_at.

This test pins that carve-out: the manual-paste path produces a Lead whose
``captured_at`` matches the ``RawPost.created_at`` synthesized at paste-time
inside ``_to_raw``. If someone routes ``_legacy.py`` through
``_process_post`` (which rejects empty timestamps) without re-thinking this
contract, this test surfaces the regression.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from consumer.sources.facebook._legacy import analyze_manual_posts


def test_paste_time_becomes_captured_at():
    """A manual paste at time T produces a Lead with captured_at ~= T.

    We don't pin T exactly (no freezegun in requirements) — we assert
    captured_at is a parseable ISO timestamp within a small window around
    when ``analyze_manual_posts`` was called. This proves the operator-
    paste-time pathway is intentional and that captured_at is sourced from
    the synthesized RawPost.created_at, not left empty.
    """
    before = datetime.now(timezone.utc)
    leads = analyze_manual_posts(
        ["Wie heeft tip voor warmtepomp installateur Utrecht? Spoed gezocht."],
        platform="facebook",
        niche="warmtepomp",
        niche_keywords=["warmtepomp", "installateur"],
        min_score=0,
    )
    after = datetime.now(timezone.utc)

    assert len(leads) == 1, "single non-empty paste must produce a lead (min_score=0)"
    lead = leads[0]

    # captured_at must be set (the doctrinal commitment).
    assert lead.captured_at, "manual-paste Lead must carry an explicit captured_at"

    # captured_at must equal created_at — both come from the same paste-time
    # synthesis in _to_raw; this is the carve-out contract.
    assert lead.captured_at == lead.created_at, (
        "operator-paste-time: captured_at and created_at must agree "
        "(both sourced from _to_raw paste-time synthesis)"
    )

    # captured_at must fall inside the call window (paste-time, not a
    # stale or fabricated value from elsewhere).
    parsed = datetime.fromisoformat(lead.captured_at.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    assert before - timedelta(seconds=2) <= parsed <= after + timedelta(seconds=2), (
        f"captured_at {parsed} must fall inside paste window [{before}, {after}] — "
        "this is the operator-paste-time carve-out per doctrine §00.4."
    )


def test_paste_time_marked_as_manual_input():
    """The synthesized RawPost is tagged so the carve-out is auditable.

    Without this tag, the paste-time captured_at would be indistinguishable
    from a scraper-fabricated one in downstream review. We don't currently
    propagate the tag onto the Lead, but the platform label + the absence of
    a real URL ('(handmatig — geen URL)') already mark this as manual input.
    """
    leads = analyze_manual_posts(
        ["Iemand een warmtepomp installateur die op korte termijn kan?"],
        platform="facebook",
        niche="warmtepomp",
        min_score=0,
    )
    assert len(leads) == 1
    lead = leads[0]
    # The 'handmatig' URL marker is the durable audit trail that this Lead
    # came through the operator-paste path, not a scraper.
    assert "handmatig" in lead.url.lower(), (
        "manual-paste leads must carry an auditable URL marker so the "
        "paste-time captured_at carve-out is recognizable downstream."
    )
