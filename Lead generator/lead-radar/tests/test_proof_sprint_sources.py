from __future__ import annotations

import sys

import pytest

import run_consumer
from consumer import sources as sources_mod
from consumer.sources import ALL_SOURCES, PROOF_SPRINT_SOURCES, REGISTRY


def test_proof_sprint_sources_constant_exists() -> None:
    assert hasattr(sources_mod, "PROOF_SPRINT_SOURCES")
    assert "PROOF_SPRINT_SOURCES" in sources_mod.__all__


def test_proof_sprint_sources_are_canonical_reddit_baseline() -> None:
    assert isinstance(PROOF_SPRINT_SOURCES, list)
    assert PROOF_SPRINT_SOURCES == ["reddit", "reddit_new"]
    assert "reddit" in PROOF_SPRINT_SOURCES
    assert "reddit_new" in PROOF_SPRINT_SOURCES


@pytest.mark.parametrize(
    "source",
    ["tweakers", "marktplaats", "bouwinfo", "google"],
)
def test_proof_sprint_sources_exclude_noisy_sources(source: str) -> None:
    assert source not in PROOF_SPRINT_SOURCES


def test_proof_sprint_sources_are_registered_sources() -> None:
    for source in PROOF_SPRINT_SOURCES:
        assert source in REGISTRY
        assert source in ALL_SOURCES


def test_sources_parser_accepts_proof_sprint_source_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_string = ",".join(PROOF_SPRINT_SOURCES)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_consumer.py", "--niche", "warmtepomp", "--sources", source_string],
    )

    args = run_consumer.parse_args()

    assert args.sources == source_string


def test_help_text_mentions_proof_sprint_source_string(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_string = ",".join(PROOF_SPRINT_SOURCES)
    monkeypatch.setattr(sys, "argv", ["run_consumer.py", "--help"])

    with pytest.raises(SystemExit) as exc:
        run_consumer.parse_args()

    assert exc.value.code == 0
    assert f"Proof-sprint rehearsal: --sources {source_string}" in capsys.readouterr().out
