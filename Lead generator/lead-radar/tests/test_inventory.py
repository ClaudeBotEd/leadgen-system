"""Unit tests for lead-radar/consumer/inventory.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from consumer.inventory import INVENTORY_FIELDS, ensure_inventory_csv, append_inventory_row


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


class TestAppendInventoryRow:
    def test_writes_all_fields(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        append_inventory_row(
            csv_path,
            lead_id="lead-abc",
            niche="warmtepomp",
            region_nl="utrecht|amersfoort",
            intent_strength="HOT",
            captured_at="2026-05-19T08:00:00+00:00",
            approved_at="2026-05-19T09:00:00+00:00",
            expires_at="2026-06-02T08:00:00+00:00",
            source_class="burner_closed",
            reviewer_attestation="Gezien in groep X",
        )
        content = csv_path.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        assert len(lines) == 2
        row = lines[1].split(",")
        assert row[0] == "lead-abc"
        assert row[1] == "warmtepomp"
        assert row[2] == "utrecht|amersfoort"
        assert row[3] == "HOT"
        assert row[7] == "burner_closed"
        assert row[8] == "Gezien in groep X"

    def test_default_optional_fields_empty(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        append_inventory_row(
            csv_path,
            lead_id="lead-xyz",
            niche="isolatie",
            region_nl="zuid-holland|rotterdam",
            intent_strength="WARM",
            captured_at="2026-05-19T08:00:00+00:00",
            approved_at="2026-05-19T09:00:00+00:00",
            expires_at="2026-06-30T08:00:00+00:00",
            source_class="apify_public",
        )
        content = csv_path.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        row = lines[1].split(",")
        assert row[8] == ""
        assert row[9] == ""
        assert row[10] == ""
        assert row[11] == ""

    def test_invalid_intent_strength_raises(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        with pytest.raises(ValueError, match="intent_strength"):
            append_inventory_row(
                csv_path,
                lead_id="lead-z",
                niche="warmtepomp",
                region_nl="utrecht|utrecht",
                intent_strength="LUKEWARM",
                captured_at="2026-05-19T08:00:00+00:00",
                approved_at="2026-05-19T09:00:00+00:00",
                expires_at="2026-06-02T08:00:00+00:00",
                source_class="apify_public",
            )

    def test_invalid_source_class_raises(self, tmp_path: Path):
        csv_path = tmp_path / "lead_inventory.csv"
        with pytest.raises(ValueError, match="source_class"):
            append_inventory_row(
                csv_path,
                lead_id="lead-z",
                niche="warmtepomp",
                region_nl="utrecht|utrecht",
                intent_strength="HOT",
                captured_at="2026-05-19T08:00:00+00:00",
                approved_at="2026-05-19T09:00:00+00:00",
                expires_at="2026-06-02T08:00:00+00:00",
                source_class="reddit",
            )


from consumer.inventory import load_decay_windows


class TestDecayWindowsConfig:
    def test_loads_windows_from_yaml(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            """
inventory:
  decay_windows:
    warmtepomp:
      HOT: 14
      WARM: 28
    isolatie:
      HOT: 21
      WARM: 42
""",
            encoding="utf-8",
        )
        windows = load_decay_windows(cfg)
        assert windows["warmtepomp"]["HOT"] == 14
        assert windows["warmtepomp"]["WARM"] == 28
        assert windows["isolatie"]["HOT"] == 21
        assert windows["isolatie"]["WARM"] == 42

    def test_missing_inventory_section_raises(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("scrapers:\n  - foo\n", encoding="utf-8")
        with pytest.raises(KeyError, match="inventory"):
            load_decay_windows(cfg)


from datetime import datetime, timezone

from consumer.inventory import compute_expires_at


class TestComputeExpiresAt:
    def test_warmtepomp_hot_14_days(self):
        windows = {"warmtepomp": {"HOT": 14, "WARM": 28}}
        captured = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
        result = compute_expires_at(captured, "warmtepomp", "HOT", windows)
        assert result == datetime(2026, 6, 2, 8, 0, 0, tzinfo=timezone.utc)

    def test_isolatie_warm_42_days(self):
        windows = {"isolatie": {"HOT": 21, "WARM": 42}}
        captured = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
        result = compute_expires_at(captured, "isolatie", "WARM", windows)
        assert result == datetime(2026, 6, 30, 8, 0, 0, tzinfo=timezone.utc)

    def test_unknown_niche_raises(self):
        windows = {"warmtepomp": {"HOT": 14, "WARM": 28}}
        captured = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(KeyError, match="niche"):
            compute_expires_at(captured, "tovenarij", "HOT", windows)

    def test_unknown_intent_strength_raises(self):
        windows = {"warmtepomp": {"HOT": 14, "WARM": 28}}
        captured = datetime(2026, 5, 19, 8, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(KeyError, match="intent_strength"):
            compute_expires_at(captured, "warmtepomp", "TEPID", windows)
