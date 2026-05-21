"""Crash-safe filesystem helpers for the FB scraper.

Three concerns centralized here:

1. ``atomic_write_json`` — writes to a temp file in the same directory, then
   ``os.replace`` swaps it in atomically.  A crash mid-write leaves the
   original file intact; partial writes are never observable.

2. ``acquire_pool_lock`` — an exclusive flock at ``data/fb_state/.lock`` so
   overlapping cron entries (12:00 still running when 17:00 fires) exit
   cleanly instead of corrupting status.json or fighting over Chromium
   profile directories.

3. ``cleanup_chromium_singletons`` — Chromium leaves ``SingletonLock``,
   ``SingletonCookie``, ``SingletonSocket`` behind after a non-clean
   shutdown (Ctrl-C during run, SIGKILL, crash).  Subsequent launches with
   the same ``user_data_dir`` will hang with a misleading error.  Sweep
   these on every session start.
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

log = logging.getLogger("consumer.sources.facebook.state_io")


class PoolLockHeld(RuntimeError):
    """Raised when another process holds the pool flock."""


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON to ``path`` atomically.

    Writes to ``<path>.tmp`` in the same directory, fsyncs, then
    ``os.replace`` swaps it into place.  Same-filesystem rename is atomic
    on POSIX so readers always see either the old file or the fully-written
    new file — never a half-written state.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


@contextmanager
def acquire_pool_lock(lock_path: Path, timeout: float = 0.0) -> Iterator[None]:
    """Acquire an exclusive flock; raise PoolLockHeld if already held.

    ``timeout=0.0`` is non-blocking — return immediately if held.  Caller
    decides whether to wait or exit.  The lock is released when the context
    manager exits, even on exception.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.touch(exist_ok=True)
    fh = lock_path.open("r")
    try:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PoolLockHeld(f"pool lock held by another process: {lock_path}")
        yield
    finally:
        try:
            fcntl.flock(fh, fcntl.LOCK_UN)
        finally:
            fh.close()


def cleanup_chromium_singletons(profile_dir: Path) -> None:
    """Remove stale Chromium singleton files left behind by a non-clean exit.

    Safe to call on a profile that has never been used (profile_dir missing)
    or that is currently in use (the files we sweep are only meaningful
    while Chromium is actively running, and a separate process holding the
    profile would have its own lock anyway).
    """
    if not profile_dir.exists():
        return
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        p = profile_dir / name
        try:
            if p.is_symlink() or p.exists():
                p.unlink()
                log.debug("swept %s", p)
        except OSError as exc:
            log.warning("could not sweep %s: %s", p, exc)
