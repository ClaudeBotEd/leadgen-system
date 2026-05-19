"""Unit tests for sweep_expired_inventory."""
from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from consumer.inventory import (
    append_inventory_row,
    sweep_expired_inventory,
)


@pytest.fixture
def inventory_with_rows(tmp_path: Path) -> tuple[Path, Path]:
    """Fixture: inventory met 1 overdue rij en 1 nog-binnen-window rij.
    Returns (inventory_path, lead_log_path).
    """
    inventory_path = tmp_path / "data" / "lead_inventory.csv"
    lead_log_path = tmp_path / "data" / "lead_log.csv"

    now = datetime.now(timezone.utc)
    overdue = (now - timedelta(days=1)).isoformat(timespec="seconds")
    fresh = (now + timedelta(days=14)).isoformat(timespec="seconds")

    append_inventory_row(
        inventory_path,
        lead_id="lead-overdue",
        niche="warmtepomp",
        region_nl="utrecht|amersfoort",
        intent_strength="HOT",
        captured_at=(now - timedelta(days=15)).isoformat(timespec="seconds"),
        approved_at=(now - timedelta(days=14)).isoformat(timespec="seconds"),
        expires_at=overdue,
        source_class="apify_public",
    )
    append_inventory_row(
        inventory_path,
        lead_id="lead-fresh",
        niche="warmtepomp",
        region_nl="utrecht|utrecht",
        intent_strength="HOT",
        captured_at=now.isoformat(timespec="seconds"),
        approved_at=now.isoformat(timespec="seconds"),
        expires_at=fresh,
        source_class="apify_public",
    )
    return inventory_path, lead_log_path


class TestSweepExpiredInventory:
    def test_writes_expired_transition_for_overdue(
        self, inventory_with_rows: tuple[Path, Path]
    ):
        inventory_path, lead_log_path = inventory_with_rows
        expired_ids = sweep_expired_inventory(
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            actor="cron",
        )
        assert expired_ids == ["lead-overdue"]
        with lead_log_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["lead_id"] == "lead-overdue"
        assert rows[0]["to_state"] == "EXPIRED"
        assert rows[0]["actor"] == "cron"

    def test_idempotent_skip_already_expired(
        self, inventory_with_rows: tuple[Path, Path]
    ):
        inventory_path, lead_log_path = inventory_with_rows
        sweep_expired_inventory(
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            actor="cron",
        )
        result = sweep_expired_inventory(
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            actor="cron",
        )
        assert result == []
        with lead_log_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1

    def test_skips_already_delivered(self, tmp_path: Path):
        inventory_path = tmp_path / "data" / "lead_inventory.csv"
        lead_log_path = tmp_path / "data" / "lead_log.csv"
        now = datetime.now(timezone.utc)
        overdue = (now - timedelta(days=1)).isoformat(timespec="seconds")
        append_inventory_row(
            inventory_path,
            lead_id="lead-delivered",
            niche="warmtepomp",
            region_nl="utrecht|utrecht",
            intent_strength="HOT",
            captured_at=(now - timedelta(days=15)).isoformat(timespec="seconds"),
            approved_at=(now - timedelta(days=14)).isoformat(timespec="seconds"),
            expires_at=overdue,
            source_class="apify_public",
            delivered_to="installer-7",
        )
        result = sweep_expired_inventory(
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            actor="cron",
        )
        assert result == []

    def test_naive_datetime_treated_as_utc(self, tmp_path: Path):
        inventory_path = tmp_path / "data" / "lead_inventory.csv"
        lead_log_path = tmp_path / "data" / "lead_log.csv"
        now = datetime.now(timezone.utc)
        # Naive datetime (no tzinfo) for expires_at — should not crash
        overdue_naive = (now - timedelta(days=1)).replace(tzinfo=None).isoformat(timespec="seconds")
        append_inventory_row(
            inventory_path,
            lead_id="lead-naive",
            niche="warmtepomp",
            region_nl="utrecht|utrecht",
            intent_strength="HOT",
            captured_at=(now - timedelta(days=15)).isoformat(timespec="seconds"),
            approved_at=(now - timedelta(days=14)).isoformat(timespec="seconds"),
            expires_at=overdue_naive,
            source_class="apify_public",
        )
        result = sweep_expired_inventory(
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            actor="cron",
        )
        assert result == ["lead-naive"]


import subprocess
import sys


class TestCLI:
    def test_dry_run_exits_zero(self, inventory_with_rows: tuple[Path, Path]):
        inventory_path, lead_log_path = inventory_with_rows
        result = subprocess.run(
            [
                sys.executable,
                "run_inventory_sweep.py",
                "--inventory", str(inventory_path),
                "--lead-log", str(lead_log_path),
                "--dry-run",
            ],
            cwd="/Users/claudebot/Lead generator/lead-radar",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "DRY-RUN" in result.stdout
        assert "lead-overdue" in result.stdout
        if lead_log_path.exists():
            with lead_log_path.open("r", encoding="utf-8") as f:
                content = f.read()
            assert "EXPIRED" not in content

    def test_actual_run_writes_to_lead_log(
        self, inventory_with_rows: tuple[Path, Path]
    ):
        inventory_path, lead_log_path = inventory_with_rows
        result = subprocess.run(
            [
                sys.executable,
                "run_inventory_sweep.py",
                "--inventory", str(inventory_path),
                "--lead-log", str(lead_log_path),
            ],
            cwd="/Users/claudebot/Lead generator/lead-radar",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "1 expired" in result.stdout
        with lead_log_path.open("r", encoding="utf-8") as f:
            content = f.read()
        assert "lead-overdue" in content
        assert "EXPIRED" in content
