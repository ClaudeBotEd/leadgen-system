"""Unit tests for seed_demo_inventory."""
from __future__ import annotations

import csv
from pathlib import Path

from run_seed_demo_inventory import DEMO_LEADS, seed_demo_inventory


def _read_inventory(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class TestSeedDemoInventory:
    def test_seeds_all_demo_leads_to_empty_csv(self, tmp_path: Path):
        inventory_path = tmp_path / "lead_inventory.csv"
        decay_windows = {
            row["niche"]: {"HOT": 14, "WARM": 28} for row in DEMO_LEADS
        }
        written = seed_demo_inventory(
            inventory_path=inventory_path,
            decay_windows=decay_windows,
        )
        assert written == len(DEMO_LEADS)
        rows = _read_inventory(inventory_path)
        assert len(rows) == len(DEMO_LEADS)
        assert {r["lead_id"] for r in rows} == {l["lead_id"] for l in DEMO_LEADS}

    def test_idempotent_skips_existing_lead_ids(self, tmp_path: Path):
        inventory_path = tmp_path / "lead_inventory.csv"
        decay_windows = {
            row["niche"]: {"HOT": 14, "WARM": 28} for row in DEMO_LEADS
        }
        seed_demo_inventory(
            inventory_path=inventory_path,
            decay_windows=decay_windows,
        )
        second = seed_demo_inventory(
            inventory_path=inventory_path,
            decay_windows=decay_windows,
        )
        assert second == 0
        rows = _read_inventory(inventory_path)
        assert len(rows) == len(DEMO_LEADS)
