"""reviewer_name must be safe for the email From header.

RFC 5322 header injection via newline/CRLF/angle-bracket payloads in a
display name is the canonical attack on email-builder code. The
reviewer_name field flows straight into `From: {name} <{addr}>`
construction in delivery/send.py — therefore the validator must reject
characters that can break header parsing.
"""

from datetime import datetime, timezone

import pytest

from delivery.model import ReviewedLead


def _valid_kwargs(**overrides) -> dict:
    base = dict(
        lead_id="L-TEST-002",
        snippet="Iemand zoekt een airco-installatie.",
        source_url="https://reddit.com/r/test",
        source_platform="reddit",
        captured_at=datetime(2026, 5, 18, 8, 0, tzinfo=timezone.utc),
        region="Utrecht",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Test reden",
        reviewer_name="Marieke de Vries",
        reviewer_email="marieke@lead-radar.nl",
        reviewed_at=datetime(2026, 5, 18, 8, 30, tzinfo=timezone.utc),
    )
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "bad_name",
    [
        "Eve\nBcc: attacker@evil.com",
        "Eve\rBcc: attacker@evil.com",
        "Eve\r\nBcc: x@evil.com",
        "Eve <attacker@evil.com>",
        "<script>",
        "Eve >",
        "Eve\x00null",
    ],
)
def test_reviewer_name_rejects_unsafe_chars(bad_name):
    with pytest.raises(ValueError, match="reviewer_name"):
        ReviewedLead(**_valid_kwargs(reviewer_name=bad_name))


@pytest.mark.parametrize(
    "good_name",
    [
        "Marieke de Vries",
        "Jan-Pieter Janssen",
        "José Núñez",
        "O'Brien",
        "Anne-Marie",
    ],
)
def test_reviewer_name_accepts_normal_names(good_name):
    lead = ReviewedLead(**_valid_kwargs(reviewer_name=good_name))
    assert lead.reviewer_name == good_name
