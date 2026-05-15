"""Wall-clock budget — voorkomt dat run_daily uren doorloopt op trage source.

Bij --max-runtime-minutes N stopt run_daily met nieuwe niches starten zodra
elapsed > N min.  Niche die op dat moment draait maakt af; volgende niches
worden geskipped.  Per-niche sheets-sync zorgt dat tussen-resultaten al
gepersist zijn.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pytest


def _minimal_daily_args(tmp_path: Path, cfg_path: Path, *,
                        max_runtime_minutes: float = 0.0,
                        sources: str = "reddit_new") -> argparse.Namespace:
    return argparse.Namespace(
        daily=True,
        location=None,
        locations="nederland",
        sources=sources,
        niche=None,
        limit=10,
        max_queries=1,
        min_score=30,
        max_age_days=0,
        max_runtime_minutes=max_runtime_minutes,
        queries_file=str(cfg_path),
        outdir=str(tmp_path),
        no_dedup=True,
        no_fuzzy_dedup=True,
        no_author_enrich=True,
        no_hardblock=True,
        no_llm=True,
        no_telegram=True,
        facebook_file=None,
        manual_file=None,
        manual_platform="facebook",
        dedup_threshold=0.85,
        llm_min_score=40,
        llm_max_score=75,
        telegram_threshold=80,
        sheets=False,
        spreadsheet_id=None,
        credentials=None,
        dry_run=True,
        verbose=False,
    )


def test_max_runtime_minutes_arg_exists() -> None:
    """CLI moet --max-runtime-minutes flag exposen."""
    import run_consumer
    import sys
    argv_backup = sys.argv
    sys.argv = ["run_consumer.py", "--daily", "--max-runtime-minutes", "30"]
    try:
        args = run_consumer.parse_args()
        assert hasattr(args, "max_runtime_minutes")
        assert args.max_runtime_minutes == 30.0
    finally:
        sys.argv = argv_backup


def test_run_daily_skips_remaining_niches_when_budget_exceeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Bij budget overschreden tussen niche 1 en 2: niche 2+ worden geskipped."""
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

    niche_calls: list[str] = []

    def tracking_source(query, *, limit, location, session, **_):  # noqa: ANN001, ANN201
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "reddit_new", tracking_source)

    orig_run_one_niche = run_consumer.run_one_niche

    def tracking_run_one_niche(args, niche, **kwargs):  # noqa: ANN001, ANN003, ANN201
        niche_calls.append(niche)
        return orig_run_one_niche(args, niche, **kwargs)

    monkeypatch.setattr(run_consumer, "run_one_niche", tracking_run_one_niche)

    # Mock monotonic clock: na 1e niche springt elapsed naar 100s (ver over budget)
    clock_values = iter([0.0, 0.1, 100.0, 100.1, 100.2, 100.3, 100.4, 100.5, 100.6])

    def fake_clock() -> float:
        try:
            return next(clock_values)
        except StopIteration:
            return 999.9

    monkeypatch.setattr(run_consumer, "_monotonic", fake_clock)

    args = _minimal_daily_args(
        tmp_path, cfg_path,
        max_runtime_minutes=0.5,  # 30 sec budget
        sources="reddit_new",
    )
    with caplog.at_level(logging.WARNING):
        run_consumer.run_daily(args)

    assert "warmtepomp" in niche_calls, f"Eerste niche niet gedraaid? calls={niche_calls}"
    assert "airco" not in niche_calls, (
        f"Tweede niche moet geskipped zijn na budget overschreden; calls={niche_calls}"
    )
    assert any("budget" in r.message.lower() for r in caplog.records), (
        "Verwacht warning over budget overschreden in logs"
    )


def test_run_daily_no_budget_runs_all_niches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """max_runtime_minutes=0 = geen budget; alle niches moeten runnen."""
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

    niche_calls: list[str] = []
    orig_run_one_niche = run_consumer.run_one_niche

    def tracking_run_one_niche(args, niche, **kwargs):  # noqa: ANN001, ANN003, ANN201
        niche_calls.append(niche)
        return orig_run_one_niche(args, niche, **kwargs)

    monkeypatch.setattr(run_consumer, "run_one_niche", tracking_run_one_niche)

    args = _minimal_daily_args(
        tmp_path, cfg_path,
        max_runtime_minutes=0.0,
        sources="reddit_new",
    )
    run_consumer.run_daily(args)

    assert "warmtepomp" in niche_calls
    assert "airco" in niche_calls
