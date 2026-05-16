"""Apify API wrapper with daily budget guardrails.

Thin layer over the official ``apify-client`` SDK.  Centralizes:

* Token discovery from env (``APIFY_API_TOKEN``).
* Hard daily spend cap (``APIFY_DAILY_BUDGET_USD``) tracked in
  ``data/apify_spend.json`` — refuses further actor calls once the cap is
  reached today.  State auto-resets at UTC midnight.
* Synchronous ``run_actor()`` that blocks until the run finishes and
  returns parsed dataset items plus the run's reported USD cost.
* Per-run timeout and one transient retry on network errors.

Everything else (per-actor input shape, item → RawPost mapping) lives in
caller modules (``apify_groups.py`` etc.) so this file stays generic.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("consumer.sources.facebook.apify_client")


class ApifyBudgetExceeded(RuntimeError):
    """Raised when today's accumulated Apify spend would exceed the cap."""


class ApifyNotConfigured(RuntimeError):
    """Raised when APIFY_API_TOKEN is missing — callers should skip gracefully."""


@dataclass
class ActorRunResult:
    """Outcome of a single actor invocation."""
    actor_id: str
    run_id: str
    items: list[dict[str, Any]]
    cost_usd: float
    finished_at: str  # ISO 8601


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_spend(path: Path) -> dict[str, float]:
    """Return {YYYY-MM-DD: usd_spent} ledger, empty dict if missing/corrupt."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: float(v) for k, v in data.items()}
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("apify_spend ledger unreadable (%s) — starting fresh", exc)
        return {}


def _write_spend(path: Path, ledger: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cutoff = sorted(ledger.keys())[-30:] if len(ledger) > 30 else list(ledger.keys())
    trimmed = {k: ledger[k] for k in cutoff}
    path.write_text(json.dumps(trimmed, indent=2, sort_keys=True), encoding="utf-8")


class ApifyRunner:
    """Budget-aware Apify actor runner.

    Construct once per process; call ``run_actor()`` per target.  All calls
    share the same ledger, so the budget cap holds across niches/groups
    within a single ``python -m ... apify`` invocation AND across separate
    invocations on the same day.
    """

    def __init__(
        self,
        *,
        token: str | None = None,
        daily_budget_usd: float | None = None,
        ledger_path: Path | None = None,
    ) -> None:
        from apify_client import ApifyClient  # late import — keeps tests light

        self._token = token or os.environ.get("APIFY_API_TOKEN", "").strip()
        if not self._token:
            raise ApifyNotConfigured(
                "APIFY_API_TOKEN is empty — set it in .env or shell to use Apify."
            )

        if daily_budget_usd is None:
            env_val = os.environ.get("APIFY_DAILY_BUDGET_USD", "").strip()
            try:
                daily_budget_usd = float(env_val) if env_val else 5.00
            except ValueError:
                log.warning("APIFY_DAILY_BUDGET_USD=%r invalid — defaulting to 5.00", env_val)
                daily_budget_usd = 5.00
        self._budget_usd = daily_budget_usd

        if ledger_path is None:
            repo_root = Path(__file__).resolve().parents[3]
            ledger_path = repo_root / "data" / "apify_spend.json"
        self._ledger_path = ledger_path

        self._client = ApifyClient(self._token)
        log.info(
            "ApifyRunner ready — daily cap $%.2f, ledger at %s",
            self._budget_usd, self._ledger_path,
        )

    @property
    def spent_today_usd(self) -> float:
        return _read_spend(self._ledger_path).get(_today_utc(), 0.0)

    @property
    def remaining_today_usd(self) -> float:
        return max(0.0, self._budget_usd - self.spent_today_usd)

    def _charge(self, cost_usd: float) -> None:
        ledger = _read_spend(self._ledger_path)
        today = _today_utc()
        ledger[today] = round(ledger.get(today, 0.0) + cost_usd, 4)
        _write_spend(self._ledger_path, ledger)
        log.info(
            "apify: charged $%.4f — today total $%.4f / $%.2f cap",
            cost_usd, ledger[today], self._budget_usd,
        )

    def run_actor(
        self,
        actor_id: str,
        run_input: dict[str, Any],
        *,
        timeout_secs: int = 600,
        memory_mbytes: int | None = None,
    ) -> ActorRunResult:
        """Invoke an Apify actor, block until done, return items + cost.

        Refuses pre-flight if today's spend already meets/exceeds the cap.
        Once the run finishes, the actual reported USD cost is added to the
        ledger — even if a single run pushes us over the cap.  This is by
        design: we can't refund a run we already paid for, but we will
        refuse the NEXT call.
        """
        if self.remaining_today_usd <= 0:
            raise ApifyBudgetExceeded(
                f"Daily Apify budget exhausted: spent ${self.spent_today_usd:.4f} "
                f"of ${self._budget_usd:.2f} on {_today_utc()}"
            )

        log.info("apify: starting %s (timeout %ds, input keys=%s)",
                 actor_id, timeout_secs, sorted(run_input.keys()))

        attempts = 0
        while True:
            attempts += 1
            try:
                run = self._client.actor(actor_id).call(
                    run_input=run_input,
                    timeout_secs=timeout_secs,
                    memory_mbytes=memory_mbytes,
                )
                break
            except Exception as exc:
                log.warning("apify: %s call failed attempt %d: %s", actor_id, attempts, exc)
                if attempts >= 2:
                    raise
                time.sleep(3.0)

        if run is None:
            raise RuntimeError(f"apify: actor {actor_id} returned None — likely timeout/abort")

        status = run.get("status", "UNKNOWN")
        run_id = run.get("id", "?")
        cost_usd = float(run.get("usageTotalUsd") or 0.0)
        dataset_id = run.get("defaultDatasetId")

        if status != "SUCCEEDED":
            self._charge(cost_usd)
            raise RuntimeError(
                f"apify: actor {actor_id} run {run_id} ended status={status} cost=${cost_usd:.4f}"
            )

        items: list[dict[str, Any]] = []
        if dataset_id:
            items = list(self._client.dataset(dataset_id).iterate_items())

        self._charge(cost_usd)
        finished = run.get("finishedAt") or datetime.now(timezone.utc).isoformat(timespec="seconds")
        log.info(
            "apify: %s run %s ok — %d items, $%.4f",
            actor_id, run_id, len(items), cost_usd,
        )
        return ActorRunResult(
            actor_id=actor_id,
            run_id=run_id,
            items=items,
            cost_usd=cost_usd,
            finished_at=finished,
        )


def is_configured() -> bool:
    """True iff APIFY_API_TOKEN is set — used by CLI to skip cleanly."""
    return bool(os.environ.get("APIFY_API_TOKEN", "").strip())


__all__ = [
    "ApifyRunner",
    "ActorRunResult",
    "ApifyBudgetExceeded",
    "ApifyNotConfigured",
    "is_configured",
]
