"""Sheets row-builder writes lead.source_id (granular) into the bron column.

We do not mock gspread — we test the pure row-builder in isolation.
"""
from __future__ import annotations

from consumer import Lead
from consumer.output import sheets as sheets_mod


def _row_for(lead: Lead) -> list:
    """Pull the row-builder. Adapt name once you've extracted it in sheets.py."""
    return sheets_mod._build_sheet_row(lead)


def test_bron_uses_source_id_when_set():
    lead = Lead(
        id="x", source="reddit", source_id="reddit:r/duurzaam",
        title="t", text="b", summary="A lead summary of at least 30 characters here for sure.",
        url="https://reddit.com/r/duurzaam/x",
        city="amsterdam", score=82, intent="hot",
        breakdown={}, niche="warmtepomp",
    )
    row = _row_for(lead)
    bron_idx = sheets_mod.SHEET_COLUMNS.index("bron")
    assert row[bron_idx] == "reddit:r/duurzaam"


def test_bron_falls_back_to_source_when_source_id_missing():
    """Lead.__post_init__ sets source_id = source if not provided, so bron
    should still equal source for a lead built without explicit source_id."""
    lead = Lead(
        id="x", source="reddit",
        title="t", text="b", summary="A lead summary of at least 30 characters here for sure.",
        url="https://reddit.com/x",
        city="amsterdam", score=82, intent="hot",
        breakdown={}, niche="warmtepomp",
    )
    row = _row_for(lead)
    bron_idx = sheets_mod.SHEET_COLUMNS.index("bron")
    assert row[bron_idx] == "reddit"
