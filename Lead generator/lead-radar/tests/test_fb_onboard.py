"""Tests voor FB onboarding wizard helpers (pure logic — no browser)."""
from __future__ import annotations

from pathlib import Path

from consumer.sources.facebook.onboard import (
    check_environment,
    generate_crontab,
    validate_targets_yaml,
)


# ── check_environment ──────────────────────────────────────────────────

def test_check_environment_returns_empty_when_all_present(tmp_path: Path) -> None:
    """Targets-yaml en state-dir aanwezig + playwright geïmporteerd → geen issues."""
    targets = tmp_path / "facebook_targets.yaml"
    targets.write_text("niches: {}\n", encoding="utf-8")
    state_dir = tmp_path / "fb_state"
    issues = check_environment(tmp_path, state_dir=state_dir, targets_path=targets)
    assert issues == [], f"unexpected issues: {issues}"


def test_check_environment_lists_missing_targets_yaml(tmp_path: Path) -> None:
    targets = tmp_path / "doesnotexist.yaml"
    state_dir = tmp_path / "fb_state"
    issues = check_environment(tmp_path, state_dir=state_dir, targets_path=targets)
    assert any("targets" in i.lower() and "missing" in i.lower() for i in issues), issues


def test_check_environment_creates_state_dir_if_missing(tmp_path: Path) -> None:
    """State dir wordt aangemaakt indien nog niet bestaand (idempotent)."""
    targets = tmp_path / "facebook_targets.yaml"
    targets.write_text("niches: {}\n", encoding="utf-8")
    state_dir = tmp_path / "newly_created"
    assert not state_dir.exists()
    check_environment(tmp_path, state_dir=state_dir, targets_path=targets)
    assert state_dir.exists() and state_dir.is_dir()


# ── validate_targets_yaml ──────────────────────────────────────────────

def test_validate_targets_yaml_missing_file(tmp_path: Path) -> None:
    ok, issues = validate_targets_yaml(tmp_path / "missing.yaml")
    assert ok is False
    assert any("missing" in i.lower() for i in issues)


def test_validate_targets_yaml_invalid_yaml(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("niches:\n  : invalid: : :\n", encoding="utf-8")
    ok, issues = validate_targets_yaml(p)
    assert ok is False
    assert issues, "expected at least one issue"


def test_validate_targets_yaml_no_niches(tmp_path: Path) -> None:
    p = tmp_path / "empty.yaml"
    p.write_text("defaults: {}\nniches: {}\n", encoding="utf-8")
    ok, issues = validate_targets_yaml(p)
    assert ok is False
    assert any("no niches" in i.lower() for i in issues), issues


def test_validate_targets_yaml_niche_with_no_targets(tmp_path: Path) -> None:
    """Niche zonder groups/pages/marketplace → warning (niet fataal)."""
    p = tmp_path / "empty_niche.yaml"
    p.write_text(
        "niches:\n"
        "  warmtepomp:\n"
        "    groups: []\n"
        "    pages: []\n"
        "    marketplace: []\n",
        encoding="utf-8",
    )
    ok, issues = validate_targets_yaml(p)
    assert ok is False
    assert any("warmtepomp" in i for i in issues)


def test_validate_targets_yaml_ok_with_one_target(tmp_path: Path) -> None:
    p = tmp_path / "good.yaml"
    p.write_text(
        "niches:\n"
        "  warmtepomp:\n"
        "    groups:\n"
        "      - id: '12345'\n"
        "        name: Warmtepomp NL\n",
        encoding="utf-8",
    )
    ok, issues = validate_targets_yaml(p)
    assert ok is True, issues
    assert issues == []


# ── generate_crontab ───────────────────────────────────────────────────

def test_generate_crontab_includes_account_id() -> None:
    out = generate_crontab(Path("/repo"), "/usr/bin/python3", account_id="burner1")
    assert "burner1" in out
    assert "scrape" in out


def test_generate_crontab_uses_provided_python_path() -> None:
    out = generate_crontab(Path("/repo"), "/opt/special/python", account_id="main")
    assert "/opt/special/python" in out


def test_generate_crontab_uses_provided_repo_root() -> None:
    out = generate_crontab(Path("/some/specific/path"), "/usr/bin/python3")
    assert "/some/specific/path" in out


def test_generate_crontab_has_quota_reset_line() -> None:
    out = generate_crontab(Path("/repo"), "/usr/bin/python3")
    assert "reset_quota" in out


def test_generate_crontab_default_4x_daily() -> None:
    """Default schedule = 4 scrape-runs per dag (8/12/17/21)."""
    out = generate_crontab(Path("/repo"), "/usr/bin/python3")
    scrape_lines = [ln for ln in out.splitlines() if "scrape" in ln and "* * *" in ln]
    assert len(scrape_lines) == 4


def test_generate_crontab_respects_custom_hours() -> None:
    out = generate_crontab(Path("/repo"), "/usr/bin/python3", hours=(9, 21))
    scrape_lines = [ln for ln in out.splitlines() if "scrape" in ln and "* * *" in ln]
    assert len(scrape_lines) == 2
    assert " 09 * * *" in out and " 21 * * *" in out


# ── CLI smoke ──────────────────────────────────────────────────────────

def test_onboard_subcommand_parses_and_runs(capsys) -> None:
    """`onboard --non-interactive` moet exit 0 geven en wizard-output printen."""
    from consumer.sources.facebook.runner import main

    rc = main(["onboard", "--non-interactive", "--account-id", "smoketest"])
    assert rc == 0
    captured = capsys.readouterr().out
    assert "OPERATOR ISOLATION CHECK" in captured
    assert "Crontab snippet" in captured
    assert "smoketest" in captured  # account-id ended up in cron snippet
    assert "Onboarding wizard complete" in captured


def test_onboard_help_lists_subcommand(capsys) -> None:
    """`--help` exposes the new `onboard` subcommand."""
    from consumer.sources.facebook.runner import _build_parser

    parser = _build_parser()
    help_text = parser.format_help()
    assert "onboard" in help_text
