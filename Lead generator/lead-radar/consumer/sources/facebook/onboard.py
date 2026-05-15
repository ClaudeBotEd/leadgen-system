"""Onboarding wizard helpers — pure logic, no browser dependencies.

Splitst de manual operator-stappen op in testbare brokken:

  - check_environment()    → ontbrekende dependencies/configs
  - validate_targets_yaml() → schema + niche-coverage check
  - generate_crontab()     → ready-to-paste cron snippet voor deze
                              repo + python-binary + account

De `onboard` subcommand in runner.py orkestreert deze helpers
interactief en wrap-pt de browser-stappen (login, fixture-capture).
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from .targets import load_targets


def check_environment(
    repo_root: Path,
    *,
    state_dir: Path | None = None,
    targets_path: Path | None = None,
) -> list[str]:
    """Return list of fixable issues.  Empty list = environment is clean.

    Side-effect: state_dir wordt aangemaakt als die ontbreekt (idempotent).
    """
    issues: list[str] = []

    try:
        import playwright  # noqa: F401
    except ImportError:
        issues.append("playwright python package not installed (pip install playwright)")

    if targets_path is None:
        targets_path = repo_root / "config" / "facebook_targets.yaml"
    if not targets_path.exists():
        issues.append(f"targets config missing: {targets_path}")

    if state_dir is None:
        state_dir = repo_root / "data" / "fb_state"
    state_dir.mkdir(parents=True, exist_ok=True)

    return issues


def validate_targets_yaml(path: Path) -> tuple[bool, list[str]]:
    """Return (ok, list of issues).  `ok=True` iff YAML is loadable AND
    minstens 1 niche heeft minstens 1 target (group/page/marketplace).
    """
    if not path.exists():
        return False, [f"targets file missing: {path}"]
    try:
        cfg = load_targets(path)
    except yaml.YAMLError as e:
        return False, [f"YAML parse error: {e}"]
    except ValidationError as e:
        return False, [f"schema error: {e}"]
    except Exception as e:
        return False, [f"load error ({type(e).__name__}): {e}"]

    issues: list[str] = []
    if not cfg.niches:
        issues.append("no niches configured (add `niches:` block to YAML)")
        return False, issues

    empty = [
        n for n, t in cfg.niches.items()
        if not (t.groups or t.pages or t.marketplace)
    ]
    if empty:
        issues.append(
            f"niche(s) {', '.join(empty)} have no targets — "
            "add at least one group/page/marketplace per niche"
        )
        return False, issues

    return True, []


def generate_crontab(
    repo_root: Path,
    python_path: str,
    *,
    account_id: str = "main",
    hours: tuple[int, ...] = (8, 12, 17, 21),
) -> str:
    """Return crontab snippet pre-filled with paths + account-id.

    `hours`: list van uren waarop scrape draait (default 4× daily).
    Quota-reset om middernacht is altijd inbegrepen.
    """
    lines = [
        "# Lead Radar — Facebook scraper crontab",
        f"# Generated for account: {account_id}",
        "# Install with:  crontab -e   (verify: crontab -l)",
        "",
        f"PROJECT_DIR={repo_root}",
        f"PYTHON={python_path}",
        "",
        f"# Scrape runs ({len(hours)}× daily)",
    ]
    for h in hours:
        lines.append(
            f'00 {h:02d} * * * cd "$PROJECT_DIR" && '
            f'"$PYTHON" -m consumer.sources.facebook.runner scrape '
            f'--niche all --account-id {account_id} '
            f'>> data/fb_state/cron.log 2>&1'
        )
    quota_cmd = (
        "from pathlib import Path; "
        "from consumer.sources.facebook.core.accounts import AccountPool; "
        "AccountPool(Path('data/fb_state')).reset_quota()"
    )
    lines.extend([
        "",
        "# Quota reset at midnight",
        f'0 0  * * * cd "$PROJECT_DIR" && "$PYTHON" -c "{quota_cmd}"',
    ])
    return "\n".join(lines) + "\n"
