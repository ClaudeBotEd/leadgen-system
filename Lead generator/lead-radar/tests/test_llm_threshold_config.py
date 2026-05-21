"""--llm-min-score and --llm-max-score CLI flags fall back to config.yaml.

Doctrine intent (commit 3b60bea3e): widening the LLM second-opinion band by
setting llm_verifier.min_score: 30 in config.yaml must actually take effect
at runtime. Prior to this wire-up the YAML value was dead — only the
argparse hardcoded default (40) was consulted.

Precedence: CLI flag > config.yaml > hardcoded fallback (40/75).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


def test_load_llm_verifier_config_reads_yaml(tmp_path: Path) -> None:
    """The helper reads the llm_verifier section verbatim."""
    import run_consumer

    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "llm_verifier:\n  min_score: 30\n  max_score: 80\n",
        encoding="utf-8",
    )
    cfg = run_consumer._load_llm_verifier_config(cfg_path)
    assert cfg.get("min_score") == 30
    assert cfg.get("max_score") == 80


def test_load_llm_verifier_config_missing_file_returns_empty(tmp_path: Path) -> None:
    """Missing config.yaml must not crash the run; fall back to argparse defaults."""
    import run_consumer

    cfg = run_consumer._load_llm_verifier_config(tmp_path / "does-not-exist.yaml")
    assert cfg == {}


def test_load_llm_verifier_config_missing_section_returns_empty(tmp_path: Path) -> None:
    """config.yaml without llm_verifier section returns empty dict, not None/error."""
    import run_consumer

    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("source_weights:\n  reddit: 1.0\n", encoding="utf-8")
    cfg = run_consumer._load_llm_verifier_config(cfg_path)
    assert cfg == {}


def test_parse_args_uses_config_yaml_min_score(monkeypatch: pytest.MonkeyPatch) -> None:
    """When --llm-min-score is omitted, parse_args resolves to config.yaml's value."""
    import run_consumer

    monkeypatch.setattr(
        run_consumer,
        "_load_llm_verifier_config",
        lambda _path: {"min_score": 30, "max_score": 80},
    )
    monkeypatch.setattr(sys, "argv", ["run_consumer.py", "--daily"])

    args = run_consumer.parse_args()

    assert args.llm_min_score == 30
    assert args.llm_max_score == 80


def test_parse_args_cli_overrides_config_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI flag wins over config.yaml."""
    import run_consumer

    monkeypatch.setattr(
        run_consumer,
        "_load_llm_verifier_config",
        lambda _path: {"min_score": 30, "max_score": 80},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_consumer.py", "--daily", "--llm-min-score", "55"],
    )

    args = run_consumer.parse_args()

    assert args.llm_min_score == 55
    assert args.llm_max_score == 80


def test_parse_args_falls_back_to_hardcoded_when_yaml_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty YAML section falls back to 40/75."""
    import run_consumer

    monkeypatch.setattr(
        run_consumer,
        "_load_llm_verifier_config",
        lambda _path: {},
    )
    monkeypatch.setattr(sys, "argv", ["run_consumer.py", "--daily"])

    args = run_consumer.parse_args()

    assert args.llm_min_score == 40
    assert args.llm_max_score == 75
