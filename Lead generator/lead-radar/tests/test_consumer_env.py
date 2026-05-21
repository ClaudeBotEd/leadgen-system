"""Boot-time env validation for run_consumer.py --daily.

Without LEAD_RADAR_SPREADSHEET_ID + LEAD_RADAR_GS_CREDENTIALS the pipeline
runs but silently fails Sheets sync — that's how the May-16 production
issue went undetected for a week. This test enforces a fail-fast block.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_daily_aborts_without_spreadsheet_id():
    """Daily mode must exit non-zero if Sheets vars are missing AND --no-sheets is not set."""
    env = os.environ.copy()
    env.pop("LEAD_RADAR_SPREADSHEET_ID", None)
    env.pop("LEAD_RADAR_GS_CREDENTIALS", None)

    result = subprocess.run(
        [sys.executable, "run_consumer.py", "--daily", "--check-env-only"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode != 0, f"Expected non-zero exit, got {result.returncode}"
    assert "LEAD_RADAR_SPREADSHEET_ID" in (result.stderr + result.stdout)


def test_daily_proceeds_when_no_sheets_flag_set():
    """--no-sheets must allow daily-mode to skip the env-validation block."""
    env = os.environ.copy()
    env.pop("LEAD_RADAR_SPREADSHEET_ID", None)
    env.pop("LEAD_RADAR_GS_CREDENTIALS", None)

    result = subprocess.run(
        [sys.executable, "run_consumer.py", "--daily", "--no-sheets", "--check-env-only"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, (
        f"Expected zero exit with --no-sheets, got {result.returncode}: {result.stderr}"
    )
