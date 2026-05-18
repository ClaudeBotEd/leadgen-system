"""Layer-2 cross-run dedup: persistent MinHash store, rolling 14d window."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from consumer.processor.cross_run_dedup import (
    is_cross_run_duplicate,
    record_lead_signature,
    prune_store,
)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return tmp_path / "dedup_store.jsonl"


def test_first_lead_is_not_duplicate(store):
    assert not is_cross_run_duplicate(
        text="Wie kan een warmtepomp installeren in Amsterdam?",
        store_path=store,
        threshold=0.70,
    )


def test_near_duplicate_within_window_is_caught(store):
    record_lead_signature(
        lead_id="L1",
        text="Wie kan een warmtepomp installeren in Amsterdam? Mijn cv ketel is stuk en ik wil zsm hybride warmtepomp laten plaatsen.",
        source="reddit:r/Amsterdam",
        niche="warmtepomp",
        store_path=store,
        now=datetime.now(timezone.utc),
    )
    assert is_cross_run_duplicate(
        text="Wie kan een warmtepomp installateren in Amsterdam? Mijn cv ketel is stuk en ik wil zsm hybride warmtepomp laten plaatsen.",  # near-dup, typo
        store_path=store,
        threshold=0.70,
    )


def test_unrelated_text_is_not_duplicate(store):
    record_lead_signature(
        lead_id="L1",
        text="Wie kan een warmtepomp installeren in Amsterdam?",
        source="reddit:r/Amsterdam",
        niche="warmtepomp",
        store_path=store,
        now=datetime.now(timezone.utc),
    )
    assert not is_cross_run_duplicate(
        text="Iemand een goede aannemer voor een dakkapel in Rotterdam? Geen idee waar te beginnen.",
        store_path=store,
        threshold=0.70,
    )


def test_old_signature_outside_window_is_pruned(store):
    record_lead_signature(
        lead_id="L1",
        text="warmtepomp installateur amsterdam gezocht spoed",
        source="reddit:r/Amsterdam",
        niche="warmtepomp",
        store_path=store,
        now=datetime.now(timezone.utc) - timedelta(days=20),
    )
    pruned = prune_store(store_path=store, retain_days=14)
    assert pruned == 1
    assert not is_cross_run_duplicate(
        text="warmtepomp installateur amsterdam gezocht spoed",
        store_path=store,
        threshold=0.70,
    )


def test_recording_appends_line_with_required_schema(store):
    now = datetime(2026, 5, 18, 8, 30, tzinfo=timezone.utc)
    record_lead_signature(
        lead_id="L1",
        text="warmtepomp gezocht in gent",
        source="marktplaats:diensten/gent",
        niche="warmtepomp",
        store_path=store,
        now=now,
    )
    lines = store.read_text().strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert set(rec.keys()) == {"signature", "lead_id", "captured_at", "source", "niche"}
    assert rec["lead_id"] == "L1"
    assert rec["source"] == "marktplaats:diensten/gent"
    assert rec["niche"] == "warmtepomp"


def test_prune_returns_zero_when_store_missing(tmp_path):
    missing = tmp_path / "does_not_exist.jsonl"
    assert prune_store(store_path=missing, retain_days=14) == 0


def test_is_duplicate_returns_false_when_store_missing(tmp_path):
    missing = tmp_path / "does_not_exist.jsonl"
    assert not is_cross_run_duplicate(
        text="any text",
        store_path=missing,
        threshold=0.70,
    )
