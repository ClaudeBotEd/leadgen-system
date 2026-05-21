from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import run_consumer
from consumer import RawPost


CREATED_AT = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc).isoformat()


def _queries_file(tmp_path: Path) -> Path:
    path = tmp_path / "queries.yaml"
    path.write_text(
        "niches:\n"
        "  warmtepomp:\n"
        "    keywords_required: [warmtepomp]\n"
        "    reddit_new_subs: [test]\n",
        encoding="utf-8",
    )
    return path


def _args(tmp_path: Path, *, no_llm: bool) -> argparse.Namespace:
    return argparse.Namespace(
        daily=False,
        location="nederland",
        locations=None,
        sources="reddit_new",
        niche="warmtepomp",
        limit=10,
        max_queries=1,
        min_score=0,
        max_age_days=14,
        max_runtime_minutes=0.0,
        llm_max_eur=0.0,
        queries_file=str(_queries_file(tmp_path)),
        outdir=str(tmp_path),
        no_dedup=True,
        no_fuzzy_dedup=True,
        no_author_enrich=True,
        enrich_authors=False,
        no_hardblock=True,
        no_llm=no_llm,
        no_telegram=True,
        facebook_file=None,
        manual_file=None,
        manual_platform="facebook",
        dedup_threshold=0.70,
        llm_min_score=40,
        llm_max_score=75,
        telegram_threshold=80,
        sheets=False,
        spreadsheet_id=None,
        credentials=None,
        dry_run=True,
        verbose=False,
    )


def _borderline_post() -> RawPost:
    return RawPost(
        id="reddit-test-1",
        source="reddit_new",
        source_id="reddit_new:r/test",
        url="https://reddit.example.test/r/test/comments/1",
        title="Warmtepomp installateur gezocht",
        text="Wie kan een warmtepomp installateur aanraden voor onze woning?",
        author=None,
        created_at=CREATED_AT,
    )


def _install_source(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_source(query, *, limit, location, session, **_kwargs):  # noqa: ANN001, ANN202
        assert query == "test"
        return [_borderline_post()]

    monkeypatch.setitem(run_consumer.REGISTRY, "reddit_new", fake_source)


def _summary_line(caplog: pytest.LogCaptureFixture) -> str:
    lines = [
        record.getMessage()
        for record in caplog.records
        if "raw=" in record.getMessage() and "llm_calls=" in record.getMessage()
    ]
    assert lines, "expected run_one_niche summary log with llm_calls"
    return lines[-1]


def test_run_one_niche_logs_zero_llm_calls_with_no_llm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _install_source(monkeypatch)

    def fail_verify(**_kwargs):  # noqa: ANN202
        raise AssertionError("verify_post must not run when --no-llm is set")

    monkeypatch.setattr(run_consumer, "verify_post", fail_verify)
    caplog.set_level(logging.INFO, logger="consumer.cli")

    leads = run_consumer.run_one_niche(_args(tmp_path, no_llm=True), "warmtepomp")

    assert leads
    line = _summary_line(caplog)
    assert "llm_calls=0" in line
    assert "cost=EUR0.0000" in line


def test_run_one_niche_logs_llm_calls_from_verifier_stats(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _install_source(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    class FakeAnthropic:
        def __init__(self, **_kwargs):  # noqa: ANN003
            self.messages = self

        def create(self, **_kwargs):  # noqa: ANN003, ANN202
            payload = (
                '{"kind":"lead","confidence":0.90,"refined_score":80,'
                '"is_real_lead":true,"reason":"test"}'
            )
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=payload)],
            )

    monkeypatch.setitem(
        sys.modules,
        "anthropic",
        SimpleNamespace(Anthropic=FakeAnthropic),
    )

    original_verify_post = run_consumer.verify_post

    def verify_without_repo_cache(**kwargs):  # noqa: ANN003, ANN202
        return original_verify_post(
            **kwargs,
            cache_dir=tmp_path / ".llm-verifier-cache",
        )

    monkeypatch.setattr(run_consumer, "verify_post", verify_without_repo_cache)
    caplog.set_level(logging.INFO, logger="consumer.cli")

    leads = run_consumer.run_one_niche(_args(tmp_path, no_llm=False), "warmtepomp")

    assert leads
    assert leads[0].breakdown["llm_verdict"] == "lead/0.90"
    assert leads[0].breakdown["llm_adjustment"] > 0
    line = _summary_line(caplog)
    assert "llm_calls=1" in line
    assert "cost=EUR0.0010" in line
