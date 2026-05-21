"""Lead.captured_at must be explicit; the field has no auto-default.

Doctrine §00.2 (five-thing rule) and §00.5 (honesty constraints):
captured_at is a verifiability commitment, not a system clock reading.
A Lead constructed without an explicit captured_at — i.e. a post whose
source-provenance timestamp we never saw — is a lie about provenance.

Tests:
1. Calling Lead() without captured_at raises TypeError (required field).
2. Lead() with an explicit captured_at succeeds.
"""

import pytest

from consumer import Lead


def test_lead_requires_explicit_captured_at():
    """Removing the default_factory means captured_at is required."""
    with pytest.raises(TypeError):
        Lead(
            id="L1",
            source="reddit",
            title="t",
            text="x",
            summary="x",
            url="https://x",
            city=None,
            score=70,
            intent="hot",
            breakdown={},
            niche="warmtepomp",
        )


def test_lead_accepts_explicit_captured_at():
    """Happy path: caller supplies captured_at."""
    lead = Lead(
        id="L1",
        source="reddit",
        title="t",
        text="x",
        summary="x",
        url="https://x",
        city=None,
        score=70,
        intent="hot",
        breakdown={},
        niche="warmtepomp",
        captured_at="2026-05-18T08:00:00+00:00",
    )
    assert lead.captured_at == "2026-05-18T08:00:00+00:00"
