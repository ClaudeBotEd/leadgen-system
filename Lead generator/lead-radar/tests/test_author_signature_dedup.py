"""Layer-3 author-signature dedup: same author, same niche, 30d window."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from consumer.processor.author_signature_dedup import (
    is_author_repeat,
    record_author_post,
    prune_author_store,
    SOURCES_WITH_AUTHOR,
)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return tmp_path / "author_signature.jsonl"


def test_first_author_post_is_not_repeat(store):
    assert not is_author_repeat(
        author="user42",
        niche="warmtepomp",
        store_path=store,
    )


def test_same_author_same_niche_within_window_is_repeat(store):
    record_author_post(
        author="user42",
        niche="warmtepomp",
        store_path=store,
        now=datetime.now(timezone.utc),
    )
    assert is_author_repeat(
        author="user42",
        niche="warmtepomp",
        store_path=store,
    )


def test_same_author_different_niche_is_not_repeat(store):
    record_author_post(
        author="user42",
        niche="warmtepomp",
        store_path=store,
        now=datetime.now(timezone.utc),
    )
    assert not is_author_repeat(
        author="user42",
        niche="zonnepanelen",
        store_path=store,
    )


def test_pruning_drops_records_older_than_30d(store):
    record_author_post(
        author="user42", niche="warmtepomp", store_path=store,
        now=datetime.now(timezone.utc) - timedelta(days=40),
    )
    pruned = prune_author_store(store_path=store, retain_days=30)
    assert pruned == 1


def test_author_hash_is_sha256_not_plaintext(store):
    record_author_post(
        author="user42", niche="warmtepomp", store_path=store,
        now=datetime.now(timezone.utc),
    )
    raw = store.read_text()
    assert "user42" not in raw, "author plaintext leaked into store"
    rec = json.loads(raw.splitlines()[0])
    assert len(rec["author_hash"]) == 64  # sha256 hex


def test_sources_with_author_excludes_ddg_and_marktplaats():
    """Marktplaats and DDG (google) author fields aren't reliable identities."""
    assert "google" not in SOURCES_WITH_AUTHOR
    assert "marktplaats" not in SOURCES_WITH_AUTHOR
    assert "2dehands" not in SOURCES_WITH_AUTHOR
    assert "reddit" in SOURCES_WITH_AUTHOR
    assert "klusidee_forum" in SOURCES_WITH_AUTHOR


def test_recording_updates_existing_entry(store):
    """Second post from same (author, niche) bumps last_seen + post_count."""
    t0 = datetime(2026, 5, 18, 8, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=2)
    record_author_post(author="u", niche="warmtepomp", store_path=store, now=t0)
    record_author_post(author="u", niche="warmtepomp", store_path=store, now=t1)
    lines = store.read_text().strip().splitlines()
    assert len(lines) == 1, "should update in-place, not append a new line"
    rec = json.loads(lines[0])
    assert rec["post_count"] == 2
    assert rec["first_seen"].startswith("2026-05-18T08:00")
    assert rec["last_seen"].startswith("2026-05-20T08:00")


def test_returns_false_when_store_missing(tmp_path):
    missing = tmp_path / "does_not_exist.jsonl"
    assert not is_author_repeat(author="u", niche="warmtepomp", store_path=missing)
