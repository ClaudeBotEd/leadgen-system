"""FB scraper CLI -- login | scrape | health | onboard.

Operator entry point.  Run with ``python -m consumer.sources.facebook.runner``.

Subcommands:

* ``login --account-id <id>`` -- opens a headed Chromium so the operator
  can log in to FB manually.  Saves the profile/cookies to
  ``data/fb_state/<id>/profile/`` for re-use by ``scrape``.

* ``scrape --niche {all|warmtepomp|airco|...}`` -- runs configured surfaces
  for the niche and writes a JSONL queue file under ``data/fb_queue/``.

* ``health`` -- prints per-account status (state / last run / quota).

* ``onboard --account-id <id>`` -- interactieve wizard: walks operator
  through isolation-warning, environment check, targets-YAML validation,
  and prints a custom crontab snippet.  Non-blocking on partial setups.
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
from .onboard import check_environment, generate_crontab, validate_targets_yaml

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
    from .surfaces.marketplace import MarketplaceSurface
    from .surfaces.pages import PagesSurface
    from .surfaces.base import BackoffRaised, ChallengeRaised
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
    stats: dict = {
        "posts_captured": 0,
        "errors": 0,
        "surfaces_visited": [],
        "backoffs": {},
    }
    aborted = False

    async with PlaywrightSession(account, state_dir=STATE_DIR, headless=False) as ctx:
        page = await new_stealth_page(ctx)

        for niche in niches_to_run:
            if aborted:
                break
            niche_targets = cfg.niches[niche]

            # ── Groups ────────────────────────────────────────────────
            if niche_targets.groups:
                groups = GroupsSurface(niche=niche, run_id=run_id)
                surface_backoff = False
                for tgt in niche_targets.groups:
                    if surface_backoff:
                        break
                    try:
                        posts = await groups.scrape(account, tgt, page)
                        log.info("  groups/%s (%s): %d", tgt.id, tgt.name, len(posts))
                        all_posts.extend(posts)
                        pool.consume_quota(account.id, "group_views", 1)
                    except ChallengeRaised as exc:
                        log.error("CHALLENGE in groups: %s -- aborting", exc.state.value)
                        pool.mark_challenged(account.id, reason=f"groups:{exc.state.value}")
                        stats["challenge_state"] = exc.state.value
                        aborted = True
                        break
                    except BackoffRaised as exc:
                        log.warning("BACKOFF in groups: %s -- skipping rest of surface", exc.state.value)
                        stats["backoffs"][f"groups:{niche}"] = exc.state.value
                        surface_backoff = True
                        break
                    except Exception:
                        log.exception("  groups/%s error -- continuing", tgt.id)
                        stats["errors"] += 1
                    await HumanPace.between_targets()
                stats["surfaces_visited"].append(f"groups:{niche}")
                if not aborted:
                    await HumanPace.between_surfaces()
            if aborted:
                break

            # ── Marketplace ───────────────────────────────────────────
            if niche_targets.marketplace:
                mp = MarketplaceSurface(niche=niche, run_id=run_id)
                surface_backoff = False
                for tgt in niche_targets.marketplace:
                    if surface_backoff:
                        break
                    try:
                        posts = await mp.scrape(account, tgt, page)
                        log.info("  marketplace/%s: %d", tgt.query, len(posts))
                        all_posts.extend(posts)
                        pool.consume_quota(account.id, "mp_queries", 1)
                    except ChallengeRaised as exc:
                        log.error("CHALLENGE in marketplace: %s -- aborting", exc.state.value)
                        pool.mark_challenged(account.id, reason=f"marketplace:{exc.state.value}")
                        stats["challenge_state"] = exc.state.value
                        aborted = True
                        break
                    except BackoffRaised as exc:
                        log.warning("BACKOFF in marketplace: %s -- skipping rest of surface", exc.state.value)
                        stats["backoffs"][f"marketplace:{niche}"] = exc.state.value
                        surface_backoff = True
                        break
                    except Exception:
                        log.exception("  marketplace/%s error -- continuing", tgt.query)
                        stats["errors"] += 1
                    await HumanPace.between_targets()
                stats["surfaces_visited"].append(f"marketplace:{niche}")
                if not aborted:
                    await HumanPace.between_surfaces()
            if aborted:
                break

            # ── Pages ─────────────────────────────────────────────────
            if niche_targets.pages:
                pages = PagesSurface(niche=niche, run_id=run_id)
                surface_backoff = False
                for tgt in niche_targets.pages:
                    if surface_backoff:
                        break
                    try:
                        posts = await pages.scrape(account, tgt, page)
                        log.info("  pages/%s (%s): %d", tgt.slug, tgt.name, len(posts))
                        all_posts.extend(posts)
                        pool.consume_quota(account.id, "page_views", 1)
                    except ChallengeRaised as exc:
                        log.error("CHALLENGE in pages: %s -- aborting", exc.state.value)
                        pool.mark_challenged(account.id, reason=f"pages:{exc.state.value}")
                        stats["challenge_state"] = exc.state.value
                        aborted = True
                        break
                    except BackoffRaised as exc:
                        log.warning("BACKOFF in pages: %s -- skipping rest of surface", exc.state.value)
                        stats["backoffs"][f"pages:{niche}"] = exc.state.value
                        surface_backoff = True
                        break
                    except Exception:
                        log.exception("  pages/%s error -- continuing", tgt.slug)
                        stats["errors"] += 1
                    await HumanPace.between_targets()
                stats["surfaces_visited"].append(f"pages:{niche}")

    stats["posts_captured"] = len(all_posts)
    pool.release(account, stats)
    write_jsonl(queue_file, all_posts)
    log.info("Run complete: %d posts -> %s", len(all_posts), queue_file)
    return 0


_ISOLATION_WARNING = """\
⚠ OPERATOR ISOLATION CHECK ⚠

FB linkt burner-accounts aan jouw persoonlijke account via device-graph
(IP + browser-fingerprint + gedrag).  Dat geeft twee risico's:

  1. Jouw persoonlijke FB krijgt 'verdachte activiteit' prompts.
  2. De burner krijgt sneller een ban.

Voldoe je aan minstens ÉÉN van:
  - aparte machine (laptop / Mac Mini / RPi / VPS, ~€5/m)
  - browserprofiel dat NOOIT met je echte FB ingelogd is
  - VPN met split-tunneling, alleen voor dit script

Aangeraden voor productie: alle drie gecombineerd.
"""


def _cmd_onboard(account_id: str, *, non_interactive: bool = False,
                 hours: tuple[int, ...] = (8, 12, 17, 21)) -> int:
    """Interactive wizard die de operator door de FB-onboarding loodst.

    Stap 1: isolation-waarschuwing + bevestiging
    Stap 2: environment check (playwright, targets, state-dir)
    Stap 3: targets-YAML validatie
    Stap 4: crontab snippet print
    Stap 5: warmup + monitor reminders
    Stap 6: hint voor login + scrape commando's

    `non_interactive=True` slaat alle prompts over (gebruikt bv. door tests
    en CI smoke-runs).  Returns 0 bij succes, 1 bij user-abort,
    2 bij blokkerende env-issues.
    """
    print(_ISOLATION_WARNING)
    if not non_interactive:
        ans = input("Voldoe je aan de isolation-vereisten? (y/N): ").strip().lower()
        if ans not in ("y", "yes", "j", "ja"):
            print("Onboarding aborted -- los isolation eerst op, dan rerun.")
            return 1

    print()
    print("=== Stap 2/5: Environment check ===")
    issues = check_environment(REPO_ROOT, state_dir=STATE_DIR, targets_path=TARGETS_PATH)
    if issues:
        print("Issues gevonden:")
        for it in issues:
            print(f"  - {it}")
        print("Je kunt verder gaan, maar fix deze vóór je daadwerkelijk scraped.")
    else:
        print("✓ Alles aanwezig.")

    print()
    print("=== Stap 3/5: Targets YAML validatie ===")
    ok, t_issues = validate_targets_yaml(TARGETS_PATH)
    if ok:
        print(f"✓ {TARGETS_PATH} valideert en heeft tenminste 1 target per gebruikte niche.")
    else:
        print("Issues:")
        for it in t_issues:
            print(f"  - {it}")
        print(f"Edit: {TARGETS_PATH}")

    print()
    print("=== Stap 4/5: Crontab snippet (kopieer naar `crontab -e`) ===")
    print()
    print(generate_crontab(REPO_ROOT, sys.executable, account_id=account_id, hours=hours))

    print("=== Stap 5/5: Reminders ===")
    print(f"  • Login (handmatig, eenmalig): python3 -m consumer.sources.facebook.runner login --account-id {account_id}")
    print(f"  • Warmup: browse 2-4 weken handmatig op het burner-profiel vóór automation aan gaat")
    print(f"  • Test scrape: python3 -m consumer.sources.facebook.runner scrape --niche warmtepomp --account-id {account_id}")
    print(f"  • Monitor: python3 -m consumer.sources.facebook.runner health")
    print(f"  • macOS: cron wekt geen slapende laptop -- gebruik launchd of caffeinate")
    print()
    print("✓ Onboarding wizard complete.")
    return 0


def _cmd_apify(niche_arg: str) -> int:
    """Run the Apify-cloud Facebook Groups collector for one or all niches.

    Does NOT require a logged-in burner account or Playwright -- Apify
    runs server-side with their own account pool + residential proxies.
    Output lands in the SAME data/fb_queue/*.jsonl shape as the self-
    hosted scraper, so run_consumer.py drains it identically.
    """
    from .targets import load_targets
    from .apify_client import ApifyNotConfigured, ApifyRunner, is_configured
    from .apify_groups import collect_groups

    if not TARGETS_PATH.exists():
        log.error("Targets config missing: %s", TARGETS_PATH)
        return 2
    cfg = load_targets(TARGETS_PATH)

    if niche_arg != "all" and niche_arg not in cfg.niches:
        log.error("Unknown niche %r -- available: %s",
                  niche_arg, ", ".join(cfg.niches.keys()))
        return 2

    if not is_configured():
        log.error(
            "APIFY_API_TOKEN is not set.  Add it to .env or export it, then retry.\n"
            "Token: https://console.apify.com/settings/integrations"
        )
        return 2

    try:
        runner = ApifyRunner()
    except ApifyNotConfigured as exc:
        log.error("Apify not configured: %s", exc)
        return 2

    summary = collect_groups(
        runner=runner,
        config=cfg,
        queue_dir=QUEUE_DIR,
        niche_filter=None if niche_arg == "all" else niche_arg,
    )
    log.info(
        "Apify groups run done: %d posts, $%.4f total%s (queue: %s)",
        summary["total_posts"], summary["total_cost_usd"],
        " [BUDGET HIT]" if summary["stopped_early"] else "",
        summary["queue_file"],
    )
    for row in summary["per_group"]:
        tag = "OK " if row.get("ok") else "ERR"
        log.info("  %s %s/%s: posts=%s cost=$%.4f %s",
                 tag, row["niche"], row["group_id"],
                 row.get("posts", 0), row.get("cost_usd", 0.0),
                 row.get("error", ""))
    return 0


def _cmd_health() -> int:
    import json as _json
    if not STATE_DIR.exists():
        log.info("No accounts registered (state dir missing: %s)", STATE_DIR)
        return 0
    found = False
    for acc_dir in sorted(STATE_DIR.iterdir()):
        status = acc_dir / "status.json"
        if not status.exists():
            continue
        found = True
        data = _json.loads(status.read_text(encoding="utf-8"))
        log.info("%s: state=%s last_used=%s quota=%s last_run=%s",
                 data["id"], data["state"], data.get("last_used_at"),
                 data.get("quota_remaining"), data.get("last_run_stats"))
    if not found:
        log.info("No accounts registered.  Run `login` to create one.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m consumer.sources.facebook.runner")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_login = sub.add_parser("login", help="Onboard a new FB account (manual login)")
    p_login.add_argument("--account-id", default="main")

    p_scrape = sub.add_parser("scrape", help="Run scraping for one or all niches (self-hosted)")
    p_scrape.add_argument("--niche", default="all",
                          help="Niche key from facebook_targets.yaml, or 'all'")
    p_scrape.add_argument("--account-id", default="main")

    p_apify = sub.add_parser("apify",
                             help="Run Apify-cloud scraper (groups) — no burner account needed")
    p_apify.add_argument("--niche", default="all",
                         help="Niche key from facebook_targets.yaml, or 'all'")

    sub.add_parser("health", help="Show per-account health")

    p_onboard = sub.add_parser("onboard",
                               help="Interactive operator-onboarding wizard")
    p_onboard.add_argument("--account-id", default="main")
    p_onboard.add_argument("--non-interactive", action="store_true",
                           help="Skip prompts (CI/smoke use)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _setup_logging(args.verbose)
    if args.cmd == "login":
        return asyncio.run(_cmd_login(args.account_id))
    if args.cmd == "scrape":
        return asyncio.run(_cmd_scrape(args.niche, args.account_id))
    if args.cmd == "apify":
        return _cmd_apify(args.niche)
    if args.cmd == "health":
        return _cmd_health()
    if args.cmd == "onboard":
        return _cmd_onboard(args.account_id, non_interactive=args.non_interactive)
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
