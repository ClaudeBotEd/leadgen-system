"""Integration tests for the niche-anchor gate applied before Sheets writes.

Spec:
  - sync_to_sheets receives only leads where is_niche_relevant() is True
  - CSV/JSON export path (inside run_one_niche) is unaffected (gate is
    non-mutating; filter returns a new list)
  - filter_leads_for_sheets logs 'kept X / dropped Y'

Mocks/fakes only — no external API calls, no real Sheets, no file IO.
"""
from __future__ import annotations

import argparse
import logging

import pytest

import run_consumer
from consumer import Lead


def _make_lead(*, lead_id: str, title: str, text: str, niche: str, score: int = 80) -> Lead:
    return Lead(
        id=lead_id,
        source="reddit",
        title=title,
        text=text,
        summary=text[:80],
        url=f"https://reddit.com/{lead_id}",
        city=None,
        score=score,
        intent="hot" if score >= 80 else "warm",
        breakdown={},
        niche=niche,
        captured_at="2026-05-21T12:00:00+00:00",
    )


def _warmtepomp_relevant_lead() -> Lead:
    return _make_lead(
        lead_id="ok-wp",
        title="Welke warmtepomp adviseren jullie?",
        text="Hybride warmtepomp of monoblock? Huis 1990.",
        niche="warmtepomp",
    )


def _waterschade_contaminant_lead() -> Lead:
    return _make_lead(
        lead_id="bad-water",
        title="Sanibroyeur defect, waterschade in huurwoning",
        text="Mijn sanibroyeur lekt al weken, huurconflict gaande.",
        niche="warmtepomp",
    )


def _uitbouw_contaminant_lead() -> Lead:
    return _make_lead(
        lead_id="bad-uitbouw",
        title="Vraag over uitbouw 8,5m diep",
        text="We willen onze keuken uitbreiden. Iemand ervaring met vergunning?",
        niche="warmtepomp",
    )


def test_filter_leads_for_sheets_returns_only_anchor_passing_leads() -> None:
    leads = [
        _warmtepomp_relevant_lead(),
        _waterschade_contaminant_lead(),
        _uitbouw_contaminant_lead(),
    ]
    result = run_consumer.filter_leads_for_sheets(leads, niche="warmtepomp")
    assert [lead.id for lead in result] == ["ok-wp"]


def test_filter_leads_for_sheets_does_not_mutate_input_list() -> None:
    leads = [
        _warmtepomp_relevant_lead(),
        _waterschade_contaminant_lead(),
    ]
    original_ids = [lead.id for lead in leads]
    _ = run_consumer.filter_leads_for_sheets(leads, niche="warmtepomp")
    assert [lead.id for lead in leads] == original_ids
    assert len(leads) == 2


def test_filter_leads_for_sheets_returns_new_list_object() -> None:
    leads = [_warmtepomp_relevant_lead()]
    result = run_consumer.filter_leads_for_sheets(leads, niche="warmtepomp")
    assert result is not leads


def test_filter_leads_for_sheets_logs_kept_and_dropped_counts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    leads = [
        _warmtepomp_relevant_lead(),
        _waterschade_contaminant_lead(),
        _uitbouw_contaminant_lead(),
    ]
    with caplog.at_level(logging.INFO):
        run_consumer.filter_leads_for_sheets(leads, niche="warmtepomp")
    matching = [
        rec for rec in caplog.records
        if "niche-anchor gate" in rec.getMessage()
    ]
    assert matching, "expected 'niche-anchor gate' log line"
    message = matching[-1].getMessage()
    assert "kept 1" in message and "dropped 2" in message
    assert "warmtepomp" in message


def test_filter_leads_for_sheets_empty_input_returns_empty() -> None:
    assert run_consumer.filter_leads_for_sheets([], niche="warmtepomp") == []


def test_run_single_passes_only_filtered_leads_to_sheets(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    leads = [
        _warmtepomp_relevant_lead(),
        _waterschade_contaminant_lead(),
        _uitbouw_contaminant_lead(),
    ]
    monkeypatch.setattr(
        run_consumer, "run_one_niche",
        lambda *a, **kw: leads,
    )
    monkeypatch.setattr(
        run_consumer, "_drain_fb_queue_once",
        lambda outdir: [],
    )
    captured: list[list[Lead]] = []

    def fake_sync(leads_in, **kwargs):
        captured.append(list(leads_in))
        return {
            "all_added": len(leads_in),
            "hot_added": 0,
            "opp_added": 0,
            "spreadsheet_url": "https://example.test/sheet",
        }

    monkeypatch.setattr(run_consumer, "sync_to_sheets", fake_sync)

    args = argparse.Namespace(
        niche="warmtepomp",
        outdir=str(tmp_path),
        sheets=True,
        dry_run=False,
        spreadsheet_id="dummy",
        credentials=None,
    )
    rc = run_consumer.run_single(args)
    assert rc == 0
    assert len(captured) == 1
    assert [lead.id for lead in captured[0]] == ["ok-wp"]


def test_run_single_skips_sync_when_gate_drops_all_leads(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If every lead fails the gate, sync_to_sheets must not be called."""
    leads = [
        _waterschade_contaminant_lead(),
        _uitbouw_contaminant_lead(),
    ]
    monkeypatch.setattr(run_consumer, "run_one_niche", lambda *a, **kw: leads)
    monkeypatch.setattr(run_consumer, "_drain_fb_queue_once", lambda outdir: [])
    sync_calls: list = []
    monkeypatch.setattr(
        run_consumer, "sync_to_sheets",
        lambda *a, **kw: sync_calls.append((a, kw)) or {
            "all_added": 0, "hot_added": 0, "opp_added": 0, "spreadsheet_url": ""
        },
    )

    args = argparse.Namespace(
        niche="warmtepomp",
        outdir=str(tmp_path),
        sheets=True,
        dry_run=False,
        spreadsheet_id="dummy",
        credentials=None,
    )
    run_consumer.run_single(args)
    assert sync_calls == []
