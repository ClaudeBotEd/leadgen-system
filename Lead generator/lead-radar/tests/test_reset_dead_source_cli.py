"""CLI for resetting dead-source health counters."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_reset_dead_source_cli_exists_and_runs():
    """The CLI must be invokable and exit 0 for a known source."""
    result = subprocess.run(
        [sys.executable, "scripts/reset_dead_source.py", "reddit"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "reddit" in result.stdout


def test_reset_dead_source_cli_rejects_unknown_source():
    result = subprocess.run(
        [sys.executable, "scripts/reset_dead_source.py", "nonexistent_source_xyz"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    combined = result.stderr + result.stdout
    assert "unknown" in combined.lower() or "REGISTRY" in combined


def test_reset_dead_source_cli_supports_all():
    """`--all` resets every source in REGISTRY."""
    result = subprocess.run(
        [sys.executable, "scripts/reset_dead_source.py", "--all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "reset" in result.stdout.lower()
