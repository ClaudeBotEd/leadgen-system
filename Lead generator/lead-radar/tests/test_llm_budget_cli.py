"""--llm-max-eur CLI flag wired to LEAD_RADAR_LLM_BUDGET_EUR env var.

Onderliggende budget-cap in llm_verifier wordt al via env var gestuurd
(zie test_llm_verifier.py).  Deze tests valideren de CLI-wiring.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pytest


def test_llm_max_eur_cli_flag_present() -> None:
    """parse_args moet --llm-max-eur exposen met float-type."""
    import run_consumer
    argv_backup = sys.argv
    sys.argv = ["run_consumer.py", "--daily", "--llm-max-eur", "3.50"]
    try:
        args = run_consumer.parse_args()
        assert hasattr(args, "llm_max_eur")
        assert args.llm_max_eur == 3.5
    finally:
        sys.argv = argv_backup


def test_llm_max_eur_default_zero_means_no_cap() -> None:
    """Default 0 = uit; env var wordt dan NIET gezet door run_daily."""
    import run_consumer
    argv_backup = sys.argv
    sys.argv = ["run_consumer.py", "--daily"]
    try:
        args = run_consumer.parse_args()
        assert args.llm_max_eur == 0.0
    finally:
        sys.argv = argv_backup


def test_run_daily_sets_budget_env_var_when_flag_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Met --llm-max-eur 1.5 zet run_daily LEAD_RADAR_LLM_BUDGET_EUR=1.5."""
    import run_consumer

    cfg_path = tmp_path / "queries.yaml"
    cfg_path.write_text(
        "niches:\n"
        "  cv:\n"
        "    keywords_required: [cv]\n"
        "    reddit_new_subs: [test]\n",
        encoding="utf-8",
    )

    def empty_source(query, *, limit, location, session, **_):  # noqa: ANN001, ANN201
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "reddit_new", empty_source)
    monkeypatch.delenv("LEAD_RADAR_LLM_BUDGET_EUR", raising=False)

    args = argparse.Namespace(
        daily=True, location=None, locations="nederland",
        sources="reddit_new", niche=None,
        limit=10, max_queries=1,
        min_score=30, max_age_days=0,
        max_runtime_minutes=0.0,
        llm_max_eur=1.50,
        queries_file=str(cfg_path), outdir=str(tmp_path),
        no_dedup=True, no_fuzzy_dedup=True, no_author_enrich=True,
        no_hardblock=True, no_llm=True, no_telegram=True,
        facebook_file=None, manual_file=None, manual_platform="facebook",
        dedup_threshold=0.85, llm_min_score=40, llm_max_score=75,
        telegram_threshold=80,
        sheets=False, spreadsheet_id=None, credentials=None,
        dry_run=True, verbose=False,
    )
    run_consumer.run_daily(args)

    assert os.environ.get("LEAD_RADAR_LLM_BUDGET_EUR") == "1.5", (
        f"env var moet '1.5' zijn; was {os.environ.get('LEAD_RADAR_LLM_BUDGET_EUR')!r}"
    )


def test_run_daily_does_not_set_env_var_when_flag_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Met --llm-max-eur 0 raakt env var ongezet (operator opt-out)."""
    import run_consumer

    cfg_path = tmp_path / "queries.yaml"
    cfg_path.write_text(
        "niches:\n"
        "  cv:\n"
        "    keywords_required: [cv]\n"
        "    reddit_new_subs: [test]\n",
        encoding="utf-8",
    )

    def empty_source(query, *, limit, location, session, **_):  # noqa: ANN001, ANN201
        return []

    monkeypatch.setitem(run_consumer.REGISTRY, "reddit_new", empty_source)
    monkeypatch.delenv("LEAD_RADAR_LLM_BUDGET_EUR", raising=False)

    args = argparse.Namespace(
        daily=True, location=None, locations="nederland",
        sources="reddit_new", niche=None,
        limit=10, max_queries=1,
        min_score=30, max_age_days=0,
        max_runtime_minutes=0.0,
        llm_max_eur=0.0,
        queries_file=str(cfg_path), outdir=str(tmp_path),
        no_dedup=True, no_fuzzy_dedup=True, no_author_enrich=True,
        no_hardblock=True, no_llm=True, no_telegram=True,
        facebook_file=None, manual_file=None, manual_platform="facebook",
        dedup_threshold=0.85, llm_min_score=40, llm_max_score=75,
        telegram_threshold=80,
        sheets=False, spreadsheet_id=None, credentials=None,
        dry_run=True, verbose=False,
    )
    run_consumer.run_daily(args)

    assert "LEAD_RADAR_LLM_BUDGET_EUR" not in os.environ, (
        "env var mag niet gezet zijn bij llm_max_eur=0"
    )
