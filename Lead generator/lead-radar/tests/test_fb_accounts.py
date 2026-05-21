"""Tests for AccountPool state machine + status.json persistence."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from consumer.sources.facebook.core.accounts import (
    Account,
    AccountPool,
    AccountState,
    NoActiveAccount,
)


def test_pool_with_no_accounts_raises_on_acquire(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    with pytest.raises(NoActiveAccount):
        pool.acquire()


def test_register_creates_status_json(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    pool.register("main")
    status = tmp_path / "main" / "status.json"
    assert status.exists()
    data = json.loads(status.read_text())
    assert data["state"] == "fresh"
    assert data["id"] == "main"


def test_acquire_returns_active_account(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    pool.register("main")
    pool.mark_state("main", AccountState.ACTIVE)
    acc = pool.acquire()
    assert acc.id == "main"
    assert acc.state == AccountState.ACTIVE


def test_acquire_skips_challenged_accounts(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    pool.register("a")
    pool.register("b")
    pool.mark_state("a", AccountState.CHALLENGED)
    pool.mark_state("b", AccountState.ACTIVE)
    acc = pool.acquire()
    assert acc.id == "b"


def test_acquire_accepts_warmed_state(tmp_path: Path) -> None:
    """A freshly-logged-in account is 'warmed' and eligible for use."""
    pool = AccountPool(tmp_path)
    pool.register("main")
    pool.mark_state("main", AccountState.WARMED)
    acc = pool.acquire()
    assert acc.id == "main"


def test_acquire_raises_when_all_challenged(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    pool.register("a")
    pool.mark_state("a", AccountState.CHALLENGED)
    with pytest.raises(NoActiveAccount):
        pool.acquire()


def test_mark_challenged_persists(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    pool.register("main")
    pool.mark_state("main", AccountState.ACTIVE)
    pool.mark_challenged("main", reason="checkpoint URL")
    reloaded = AccountPool(tmp_path)
    with pytest.raises(NoActiveAccount):
        reloaded.acquire()  # status persisted across instances


def test_release_records_run_stats(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    pool.register("main")
    pool.mark_state("main", AccountState.ACTIVE)
    acc = pool.acquire()
    pool.release(acc, stats={"posts_captured": 23, "errors": 0})
    data = json.loads((tmp_path / "main" / "status.json").read_text())
    assert data["last_run_stats"]["posts_captured"] == 23


def test_reset_quota_restores_defaults(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    pool.register("main")
    pool.consume_quota("main", "group_views", 50)
    pool.reset_quota()
    data = json.loads((tmp_path / "main" / "status.json").read_text())
    assert data["quota_remaining"]["group_views"] == 100


def test_consume_quota_decrements(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    pool.register("main")
    pool.consume_quota("main", "group_views", 30)
    data = json.loads((tmp_path / "main" / "status.json").read_text())
    assert data["quota_remaining"]["group_views"] == 70


def test_quota_overspend_raises(tmp_path: Path) -> None:
    pool = AccountPool(tmp_path)
    pool.register("main")
    pool.mark_state("main", AccountState.ACTIVE)
    with pytest.raises(ValueError):
        pool.consume_quota("main", "group_views", 200)
