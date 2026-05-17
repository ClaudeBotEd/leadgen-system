"""source_id is the granular label written to Sheets `bron` column.

Falls back to `source` when a source-module doesn't provide one (legacy
compat for sources we haven't updated yet).
"""
from __future__ import annotations

from consumer import Lead, RawPost


def test_raw_post_source_id_defaults_to_source():
    post = RawPost(id="x", source="reddit", url="https://example.com/x", title="t", text="b")
    assert post.source_id == "reddit"


def test_raw_post_source_id_can_be_explicit():
    post = RawPost(
        id="x",
        source="reddit",
        source_id="reddit:r/duurzaam",
        url="https://example.com/x",
        title="t",
        text="b",
    )
    assert post.source_id == "reddit:r/duurzaam"
    assert post.source == "reddit"


def test_lead_source_id_defaults_to_source():
    lead = Lead(
        id="x",
        source="marktplaats",
        title="t",
        text="b",
        summary="s",
        url="https://example.com/x",
        city="amsterdam",
        score=72,
        intent="warm",
        breakdown={},
        niche="warmtepomp",
    )
    assert lead.source_id == "marktplaats"


def test_lead_source_id_can_be_explicit():
    lead = Lead(
        id="x",
        source="marktplaats",
        source_id="marktplaats:diensten/gent",
        title="t",
        text="b",
        summary="s",
        url="https://example.com/x",
        city="gent",
        score=82,
        intent="hot",
        breakdown={},
        niche="renovatie",
    )
    assert lead.source_id == "marktplaats:diensten/gent"
    assert lead.source == "marktplaats"
