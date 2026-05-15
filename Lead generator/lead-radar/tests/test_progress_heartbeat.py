"""Progress heartbeat in run_daily — geeft operator zicht op vordering.

Bij urenlange runs (--daily --locations all) wist operator voorheen niet
of de pipeline hing of doorging.  Heartbeat logt na elke niche:
  [progress] N/M done | niche=X | elapsed=Ys | eta=Zs
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pytest


def _minimal_daily_args(tmp_path: Path, cfg_path: Path,
                        *, sources: str = "reddit_new",
                        locations: str = "nederland") -> argparse.Namespace:
    return argparse.Namespace(
        daily=True, location=None, locations=locations,
        sources=sources, niche=None,
        limit=10, max_queries=1,
        min_score=30, max_age_days=0,
        max_runtime_minutes=0.0,
        queries_file=str(cfg_path), outdir=str(tmp_path),
        no_dedup=True, no_fuzzy_dedup=True, no_author_enrich=True,
        no_hardblock=True, no_llm=True, no_telegram=True,
        facebook_file=None, manual_file=None, manual_platform="facebook",
        dedup_threshold=0.85, llm_min_score=40, llm_max_score=75,
        telegram_threshold=80,
        sheets=False, spreadsheet_id=None, credentials=None,
        dry_run=True, verbose=False,
    )


def test_progress_logged_per_niche(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Per voltooide niche: 1 progress-log entry."""
    import run_consumer

    cfg_path = tmp_path / "queries.yaml"
    cfg_path.write_text(
        "niches:\n"
        "  warmtepomp:\n"
        "    keywords_required: [warmtepomp]\n"
        "    reddit_new_subs: [test]\n"
        "  airco:\n"
        "    keywords_required: [airco]\n"
        "    reddit_new_subs: [test]\n",
        encoding="utf-8",
    )

    def empty_source(query, *, limit, location, session, **_):  # noqa: ANN001, ANN201
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "reddit_new", empty_source)

    args = _minimal_daily_args(tmp_path, cfg_path)
    with caplog.at_level(logging.INFO, logger="consumer.cli"):
        run_consumer.run_daily(args)

    progress_logs = [
        r for r in caplog.records
        if "progress" in r.message.lower() and "niche=" in r.message.lower()
    ]
    assert len(progress_logs) >= 2, (
        f"Verwacht ≥2 progress-logs (1 per niche); got {len(progress_logs)}: "
        f"{[r.message for r in progress_logs]}"
    )


def test_progress_includes_count_and_eta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Progress-log moet 'N/M' count en 'eta=' bevatten zodat ETA bruikbaar is."""
    import run_consumer

    cfg_path = tmp_path / "queries.yaml"
    cfg_path.write_text(
        "niches:\n"
        "  warmtepomp:\n"
        "    keywords_required: [warmtepomp]\n"
        "    reddit_new_subs: [test]\n"
        "  airco:\n"
        "    keywords_required: [airco]\n"
        "    reddit_new_subs: [test]\n"
        "  cv:\n"
        "    keywords_required: [cv]\n"
        "    reddit_new_subs: [test]\n",
        encoding="utf-8",
    )

    def empty_source(query, *, limit, location, session, **_):  # noqa: ANN001, ANN201
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "reddit_new", empty_source)

    args = _minimal_daily_args(tmp_path, cfg_path)
    with caplog.at_level(logging.INFO, logger="consumer.cli"):
        run_consumer.run_daily(args)

    progress_logs = [r.message for r in caplog.records if "progress" in r.message.lower()]
    assert progress_logs, "Geen progress logs gevonden"
    assert any("1/" in m for m in progress_logs), (
        f"Verwacht count-format 'N/M' in progress; got: {progress_logs}"
    )
    assert any("eta=" in m.lower() for m in progress_logs), (
        f"Verwacht 'eta=' in progress; got: {progress_logs}"
    )
