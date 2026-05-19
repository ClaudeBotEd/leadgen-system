"""Tests for atomic JSON write, pool flock, and SingletonLock cleanup."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from consumer.sources.facebook.core.state_io import (
    atomic_write_json,
    acquire_pool_lock,
    PoolLockHeld,
    cleanup_chromium_singletons,
)


def test_atomic_write_json_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    atomic_write_json(target, {"hello": "world"})
    assert json.loads(target.read_text()) == {"hello": "world"}


def test_atomic_write_json_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    target.write_text(json.dumps({"old": True}), encoding="utf-8")
    atomic_write_json(target, {"new": True})
    assert json.loads(target.read_text()) == {"new": True}


def test_atomic_write_json_does_not_leave_tmp_file(tmp_path: Path) -> None:
    target = tmp_path / "x.json"
    atomic_write_json(target, {"k": "v"})
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == [], f"atomic write left tmp file(s): {leftovers}"


def test_acquire_pool_lock_blocks_concurrent_acquire(tmp_path: Path) -> None:
    lock_path = tmp_path / ".lock"
    with acquire_pool_lock(lock_path):
        with pytest.raises(PoolLockHeld):
            with acquire_pool_lock(lock_path, timeout=0.0):
                pass


def test_acquire_pool_lock_releases_on_exit(tmp_path: Path) -> None:
    lock_path = tmp_path / ".lock"
    with acquire_pool_lock(lock_path):
        pass
    # After release, a new acquire should succeed
    with acquire_pool_lock(lock_path, timeout=0.0):
        pass


def test_cleanup_chromium_singletons_removes_stale_locks(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        (profile / name).touch()
    cleanup_chromium_singletons(profile)
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        assert not (profile / name).exists(), f"{name} not cleaned up"


def test_cleanup_chromium_singletons_missing_profile_is_noop(tmp_path: Path) -> None:
    cleanup_chromium_singletons(tmp_path / "nonexistent")  # should not raise
