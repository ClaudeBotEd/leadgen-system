"""Unit tests for lead-radar/consumer/inventory.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer.inventory import INVENTORY_FIELDS, ensure_inventory_csv


class TestInventorySchema:
    def test_fields_in_correct_order(self):
        assert INVENTORY_FIELDS == [
            "lead_id",
            "niche",
            "region_nl",
            "intent_strength",
            "captured_at",
            "approved_at",
            "expires_at",
            "source_class",
            "reviewer_attestation",
            "delivered_to",
            "demo_used_at",
            "still_warm_checked_at",
        ]


class TestEnsureInventoryCSV:
    def test_creates_csv_with_header(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        result = ensure_inventory_csv(csv_path)
        assert result == csv_path
        assert csv_path.exists()
        content = csv_path.read_text(encoding="utf-8")
        assert content.startswith(",".join(INVENTORY_FIELDS))

    def test_idempotent_on_existing_file(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        ensure_inventory_csv(csv_path)
        with csv_path.open("a", encoding="utf-8") as f:
            f.write("lead-1,warmtepomp,utrecht|amersfoort,HOT,,,,,,,,,\n")
        ensure_inventory_csv(csv_path)
        content = csv_path.read_text(encoding="utf-8")
        assert "lead-1,warmtepomp" in content
