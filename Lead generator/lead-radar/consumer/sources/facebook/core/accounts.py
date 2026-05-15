"""Account + AccountPool — per-account state and persistence.

Phase 1 typically holds a single account ("main"), but the pool interface
already supports rotation so Phase 2 can swap implementations without
touching the runner.

State is persisted to ``<state_dir>/<account_id>/status.json`` so across
process restarts the pool remembers which accounts are challenged.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


DEFAULT_QUOTAS: dict[str, int] = {
    "group_views": 100,
    "mp_queries": 50,
    "page_views": 30,
}


class AccountState(str, Enum):
    FRESH = "fresh"
    WARMED = "warmed"
    ACTIVE = "active"
    CHALLENGED = "challenged"
    DEAD = "dead"


_ACTIVE_STATES: frozenset[AccountState] = frozenset({AccountState.WARMED, AccountState.ACTIVE})


class NoActiveAccount(RuntimeError):
    """No account in WARMED/ACTIVE state available."""


@dataclass
class Account:
    id: str
    state: AccountState
    last_used_at: str | None = None
    last_run_stats: dict | None = None
    quota_remaining: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_QUOTAS))

    def profile_dir(self, state_dir: Path) -> Path:
        return state_dir / self.id / "profile"


class AccountPool:
    """File-backed pool of FB accounts.

    Each account lives under ``state_dir/<id>/`` with a ``status.json`` for
    state and a ``profile/`` directory used as the Playwright user_data_dir.
    """

    def __init__(self, state_dir: Path) -> None:
        self._dir = state_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def register(self, account_id: str) -> Account:
        """Create state directories for a new account. Idempotent."""
        acc_dir = self._dir / account_id
        acc_dir.mkdir(parents=True, exist_ok=True)
        (acc_dir / "profile").mkdir(exist_ok=True)
        status = acc_dir / "status.json"
        if not status.exists():
            acc = Account(id=account_id, state=AccountState.FRESH)
            self._write(acc)
            return acc
        return self._read(account_id)

    def acquire(self) -> Account:
        """Return the first WARMED or ACTIVE account; raise if none available."""
        for acc_dir in sorted(self._dir.iterdir()):
            if not acc_dir.is_dir():
                continue
            status = acc_dir / "status.json"
            if not status.exists():
                continue
            acc = self._read(acc_dir.name)
            if acc.state in _ACTIVE_STATES:
                acc.last_used_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                self._write(acc)
                return acc
        raise NoActiveAccount("no warmed/active accounts in pool")

    def release(self, account: Account, stats: dict) -> None:
        """Persist the run stats for the just-completed run."""
        acc = self._read(account.id)
        acc.last_run_stats = stats
        self._write(acc)

    def mark_state(self, account_id: str, state: AccountState) -> None:
        acc = self._read(account_id)
        acc.state = state
        self._write(acc)

    def mark_challenged(self, account_id: str, reason: str) -> None:
        acc = self._read(account_id)
        acc.state = AccountState.CHALLENGED
        acc.last_run_stats = {**(acc.last_run_stats or {}), "challenge_reason": reason}
        self._write(acc)

    def consume_quota(self, account_id: str, key: str, amount: int) -> None:
        acc = self._read(account_id)
        remaining = acc.quota_remaining.get(key, 0)
        if amount > remaining:
            raise ValueError(
                f"quota '{key}' exceeded for {account_id}: "
                f"requested {amount}, have {remaining}"
            )
        acc.quota_remaining[key] = remaining - amount
        self._write(acc)

    def reset_quota(self) -> None:
        for acc_dir in self._dir.iterdir():
            if not acc_dir.is_dir() or not (acc_dir / "status.json").exists():
                continue
            acc = self._read(acc_dir.name)
            acc.quota_remaining = dict(DEFAULT_QUOTAS)
            self._write(acc)

    def _read(self, account_id: str) -> Account:
        status = self._dir / account_id / "status.json"
        data = json.loads(status.read_text(encoding="utf-8"))
        data["state"] = AccountState(data["state"])
        return Account(**data)

    def _write(self, acc: Account) -> None:
        status = self._dir / acc.id / "status.json"
        data = asdict(acc)
        data["state"] = acc.state.value
        status.write_text(json.dumps(data, indent=2), encoding="utf-8")
