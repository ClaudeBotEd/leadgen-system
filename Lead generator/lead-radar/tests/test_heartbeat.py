"""Heartbeat: detect silent pipeline failure via log-mtime check.

The heartbeat script is bash, but its core decision logic is tested
via subprocess. Each test sets up a known mtime on a temp log file and
asserts the script's exit code + stdout indicates alert-or-OK.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HEARTBEAT_SH = REPO_ROOT / "scripts" / "heartbeat.sh"


@pytest.fixture
def fake_logs(tmp_path):
    """Create temp log files we can age by setting mtime."""
    apify = tmp_path / "apify.log"
    consumer = tmp_path / "consumer.log"
    apify.write_text("dummy", encoding="utf-8")
    consumer.write_text("dummy", encoding="utf-8")
    return {"apify": apify, "consumer": consumer, "dir": tmp_path}


def _set_mtime_hours_ago(path: Path, hours: float) -> None:
    """Pretend the file was touched hours ago."""
    t = time.time() - hours * 3600
    os.utime(path, (t, t))


def _run_heartbeat(logs_dir: Path, dry_run: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HEARTBEAT_LOGS_DIR"] = str(logs_dir)
    env["HEARTBEAT_DRY_RUN"] = "1" if dry_run else "0"
    env["TELEGRAM_BOT_TOKEN"] = "test-token"
    env["TELEGRAM_CHAT_ID"] = "123"
    return subprocess.run(
        ["/bin/bash", str(HEARTBEAT_SH)],
        env=env, capture_output=True, text=True, timeout=10,
    )


def test_heartbeat_ok_when_both_logs_fresh(fake_logs):
    _set_mtime_hours_ago(fake_logs["apify"], 1)
    _set_mtime_hours_ago(fake_logs["consumer"], 1)
    result = _run_heartbeat(fake_logs["dir"])
    assert result.returncode == 0, result.stderr
    assert "ALERT" not in result.stdout
    assert "OK" in result.stdout


def test_heartbeat_alerts_when_apify_too_stale(fake_logs):
    _set_mtime_hours_ago(fake_logs["apify"], 36)  # > 30h threshold
    _set_mtime_hours_ago(fake_logs["consumer"], 1)
    result = _run_heartbeat(fake_logs["dir"])
    assert "ALERT" in result.stdout
    assert "apify" in result.stdout.lower()


def test_heartbeat_alerts_when_consumer_too_stale(fake_logs):
    _set_mtime_hours_ago(fake_logs["apify"], 1)
    _set_mtime_hours_ago(fake_logs["consumer"], 12)  # > 8h threshold
    result = _run_heartbeat(fake_logs["dir"])
    assert "ALERT" in result.stdout
    assert "consumer" in result.stdout.lower()


def test_heartbeat_alerts_when_log_missing(fake_logs):
    """A missing log file is treated as a silent failure (alert)."""
    fake_logs["apify"].unlink()
    _set_mtime_hours_ago(fake_logs["consumer"], 1)
    result = _run_heartbeat(fake_logs["dir"])
    assert "ALERT" in result.stdout
    assert "apify" in result.stdout.lower()


def test_heartbeat_dry_run_does_not_send_telegram(fake_logs):
    """HEARTBEAT_DRY_RUN=1 must skip the actual curl POST."""
    _set_mtime_hours_ago(fake_logs["apify"], 36)
    result = _run_heartbeat(fake_logs["dir"], dry_run=True)
    assert "DRY_RUN" in result.stdout
    assert "https://api.telegram.org" not in result.stderr
