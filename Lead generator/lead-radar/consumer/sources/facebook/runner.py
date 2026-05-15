"""FB scraper CLI -- login | scrape | health.

Operator entry point.  Run with ``python -m consumer.sources.facebook.runner``.

Subcommands:

* ``login --account-id <id>`` -- opens a headed Chromium so the operator
  can log in to FB manually.  Saves the profile/cookies to
  ``data/fb_state/<id>/profile/`` for re-use by ``scrape``.

* ``scrape --niche {all|warmtepomp|airco|...}`` -- runs configured surfaces
  for the niche and writes a JSONL queue file under ``data/fb_queue/``.
  (Implemented in T12.)

* ``health`` -- prints per-account status (state / last run / quota).
  (Implemented in T18.)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from .core.accounts import Account, AccountPool, AccountState, NoActiveAccount
from .core.detector import ChallengeState, detect_state
from .core.session import PlaywrightSession, new_stealth_page

log = logging.getLogger("consumer.sources.facebook.runner")

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent  # consumer/sources/facebook -> repo root
STATE_DIR = REPO_ROOT / "data" / "fb_state"
QUEUE_DIR = REPO_ROOT / "data" / "fb_queue"
TARGETS_PATH = REPO_ROOT / "config" / "facebook_targets.yaml"


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def _cmd_login(account_id: str) -> int:
    pool = AccountPool(STATE_DIR)
    pool.register(account_id)
    log.info("Opening headed Chromium for account %s -- log in manually, then press ENTER.",
             account_id)
    acc = Account(id=account_id, state=AccountState.FRESH)
    async with PlaywrightSession(acc, state_dir=STATE_DIR, headless=False) as ctx:
        page = await new_stealth_page(ctx)
        await page.goto("https://www.facebook.com/login/", wait_until="domcontentloaded", timeout=30000)
        log.info("Browser is open.  Finish login (handle 2FA if prompted).")
        log.info("Press ENTER in this terminal when you are fully logged in to FB home.")
        await asyncio.to_thread(input, ">> ")
        log.info("Verifying session...")
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        state = await detect_state(page)
        if state == ChallengeState.OK:
            pool.mark_state(account_id, AccountState.WARMED)
            log.info("Account %s logged in successfully -- state=warmed.", account_id)
            return 0
        log.error("Login did not produce a clean session (state=%s). Try again.", state.value)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m consumer.sources.facebook.runner")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_login = sub.add_parser("login", help="Onboard a new FB account (manual login)")
    p_login.add_argument("--account-id", default="main")

    p_scrape = sub.add_parser("scrape", help="Run scraping for one or all niches")
    p_scrape.add_argument("--niche", default="all",
                          help="Niche key from facebook_targets.yaml, or 'all'")
    p_scrape.add_argument("--account-id", default="main")

    sub.add_parser("health", help="Show per-account health")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _setup_logging(args.verbose)
    if args.cmd == "login":
        return asyncio.run(_cmd_login(args.account_id))
    if args.cmd == "scrape":
        log.error("scrape command not yet implemented in this task -- see T12")
        return 2
    if args.cmd == "health":
        log.error("health command not yet implemented in this task -- see T18")
        return 2
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
