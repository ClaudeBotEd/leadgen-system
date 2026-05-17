"""Reproduces the May-16 production exporter error.

Error in log: invalid literal for int() with base 10: 'lead/0.85'
Triggered when breakdown contains the llm_verdict string format
produced by run_consumer.py: f"{verdict.kind}/{verdict.confidence:.2f}".
"""
from __future__ import annotations

import json

from consumer import Lead


def _make_lead(breakdown: dict) -> Lead:
    return Lead(
        id="t1",
        source="reddit",
        title="x",
        text="x",
        summary="x",
        url="https://example.com/x",
        city="amsterdam",
        score=72,
        intent="warm",
        breakdown=breakdown,
        niche="warmtepomp",
        author="someuser",
        created_at="2026-05-16T06:00:00+02:00",
    )


def test_to_dict_handles_llm_verdict_string_in_breakdown():
    """breakdown['llm_verdict'] is f'{kind}/{confidence:.2f}' from run_consumer.py:506."""
    lead = _make_lead({"keyword_match": 30, "llm_verdict": "lead/0.85"})

    d = lead.to_dict()  # must not raise

    assert d["breakdown"]["llm_verdict"] == "lead/0.85"
    assert d["breakdown"]["keyword_match"] == 30


def test_to_dict_output_is_json_serializable():
    """The downstream exporter calls json.dumps(lead.breakdown). Verify nothing trips it."""
    lead = _make_lead({
        "keyword_match": 30,
        "llm_verdict": "lead/0.85",
        "llm_adjustment": -3,
        "author_recurring": 1,
    })

    d = lead.to_dict()

    assert json.loads(json.dumps(d["breakdown"]))["llm_verdict"] == "lead/0.85"
