"""Unit tests for run_inventory_show CLI."""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer.inventory import append_inventory_row
from run_inventory_show import render_inventory_table, main


@pytest.fixture
def sample_inventory(tmp_path: Path) -> Path:
    path = tmp_path / "lead_inventory.csv"
    append_inventory_row(
        path,
        lead_id="lead-001",
        niche="warmtepomp",
        region_nl="utrecht|amersfoort",
        intent_strength="HOT",
        captured_at="2026-05-19T08:00:00+00:00",
        approved_at="2026-05-19T09:00:00+00:00",
        expires_at="2026-06-02T08:00:00+00:00",
        source_class="apify_public",
    )
    append_inventory_row(
        path,
        lead_id="lead-002",
        niche="zonnepanelen",
        region_nl="utrecht|utrecht",
        intent_strength="WARM",
        captured_at="2026-05-18T14:00:00+00:00",
        approved_at="2026-05-18T15:00:00+00:00",
        expires_at="2026-06-01T14:00:00+00:00",
        source_class="burner_closed",
        reviewer_attestation="Lid sinds 2024",
    )
    return path


class TestRenderInventoryTable:
    def test_renders_header_and_rows(self, sample_inventory: Path):
        out = render_inventory_table(sample_inventory)
        assert "lead-001" in out
        assert "lead-002" in out
        assert "warmtepomp" in out
        assert "HOT" in out
        assert "WARM" in out
        assert "intent" in out.lower()

    def test_empty_inventory_returns_message(self, tmp_path: Path):
        out = render_inventory_table(tmp_path / "missing.csv")
        assert "Geen inventory" in out or "empty" in out.lower()

    def test_main_prints_to_stdout(
        self, sample_inventory: Path, capsys: pytest.CaptureFixture
    ):
        rc = main(["--inventory", str(sample_inventory)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "lead-001" in captured.out
