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


async def _cmd_scrape(niche_arg: str, account_id: str) -> int:
    from .targets import load_targets
    from .queue import write_jsonl
    from .surfaces.groups import GroupsSurface
    from .surfaces.base import ChallengeRaised
    from .core.throttle import HumanPace
    from consumer import RawPost

    if not TARGETS_PATH.exists():
        log.error("Targets config missing: %s", TARGETS_PATH)
        return 2
    cfg = load_targets(TARGETS_PATH)

    niches_to_run = list(cfg.niches.keys()) if niche_arg == "all" else [niche_arg]
    if niche_arg != "all" and niche_arg not in cfg.niches:
        log.error("Unknown niche %r -- available: %s", niche_arg, ", ".join(cfg.niches.keys()))
        return 2

    pool = AccountPool(STATE_DIR)
    try:
        account = pool.acquire()
    except NoActiveAccount:
        log.error("No warmed/active accounts in pool.  Run `login` first.")
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M")
    queue_file = QUEUE_DIR / f"{run_id}.jsonl"

    all_posts: list[RawPost] = []
    stats: dict = {"posts_captured": 0, "errors": 0, "surfaces_visited": []}
    aborted = False

    async with PlaywrightSession(account, state_dir=STATE_DIR, headless=False) as ctx:
        page = await new_stealth_page(ctx)
        for niche in niches_to_run:
            if aborted:
                break
            niche_targets = cfg.niches[niche]
            if not niche_targets.groups:
                log.info("niche %s: no group targets, skipping", niche)
                continue
            surface = GroupsSurface(niche=niche, run_id=run_id)
            log.info("niche %s: scraping %d groups", niche, len(niche_targets.groups))
            for tgt in niche_targets.groups:
                try:
                    posts = await surface.scrape(account, tgt, page)
                    log.info("  group %s (%s): %d posts", tgt.id, tgt.name, len(posts))
                    all_posts.extend(posts)
                    pool.consume_quota(account.id, "group_views", 1)
                except ChallengeRaised as exc:
                    log.error("CHALLENGE on group %s: %s -- aborting run", tgt.id, exc.state.value)
                    pool.mark_challenged(account.id, reason=f"groups:{exc.state.value}")
                    stats["challenge_state"] = exc.state.value
                    aborted = True
                    break
                except Exception:
                    log.exception("  group %s: error -- continuing", tgt.id)
                    stats["errors"] += 1
                await HumanPace.between_targets()
            stats["surfaces_visited"].append(f"groups:{niche}")
            if not aborted and niche != niches_to_run[-1]:
                await HumanPace.between_surfaces()

    stats["posts_captured"] = len(all_posts)
    pool.release(account, stats)
    write_jsonl(queue_file, all_posts)
    log.info("Run complete: %d posts -> %s", len(all_posts), queue_file)
    return 0


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
        return asyncio.run(_cmd_scrape(args.niche, args.account_id))
    if args.cmd == "health":
        log.error("health command not yet implemented in this task -- see T18")
        return 2
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
