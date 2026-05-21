"""Unit tests for approve_lead — Plan B Task 1.

approve_lead is een transactionele wrapper:
  pcs.append_transition (NEW -> APPROVED) + inventory.append_inventory_row.

Doctrine §00.2.b: closed-group leads vereisen non-empty reviewer_attestation.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import pytest

from consumer.approval import ApprovalError, approve_lead


@pytest.fixture
def decay_windows() -> dict[str, dict[str, int]]:
    return {
        "warmtepomp": {"HOT": 7, "WARM": 21},
        "zonnepanelen": {"HOT": 5, "WARM": 14},
    }


@pytest.fixture
def captured_at() -> datetime:
    return datetime(2026, 5, 19, 9, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def paths(tmp_path: Path) -> tuple[Path, Path]:
    inventory_path = tmp_path / "data" / "lead_inventory.csv"
    lead_log_path = tmp_path / "data" / "lead_log.csv"
    return inventory_path, lead_log_path


class TestApproveLead:
    def test_writes_inventory_row_and_pcs_transition(
        self,
        paths: tuple[Path, Path],
        decay_windows: dict[str, dict[str, int]],
        captured_at: datetime,
    ):
        inventory_path, lead_log_path = paths
        approve_lead(
            lead_id="lead-001",
            niche="warmtepomp",
            region_nl="utrecht|amersfoort",
            intent_strength="HOT",
            captured_at=captured_at,
            source_class="apify_public",
            reviewer_name="sem",
            decay_windows=decay_windows,
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
        )

        with inventory_path.open("r", encoding="utf-8", newline="") as f:
            inv_rows = list(csv.DictReader(f))
        assert len(inv_rows) == 1
        assert inv_rows[0]["lead_id"] == "lead-001"
        assert inv_rows[0]["niche"] == "warmtepomp"
        assert inv_rows[0]["intent_strength"] == "HOT"
        assert inv_rows[0]["source_class"] == "apify_public"

        with lead_log_path.open("r", encoding="utf-8", newline="") as f:
            log_rows = list(csv.DictReader(f))
        assert len(log_rows) == 1
        assert log_rows[0]["lead_id"] == "lead-001"
        assert log_rows[0]["from_state"] == "NEW"
        assert log_rows[0]["to_state"] == "APPROVED"
        assert log_rows[0]["actor"] == "sem"

    def test_closed_group_requires_attestation(
        self,
        paths: tuple[Path, Path],
        decay_windows: dict[str, dict[str, int]],
        captured_at: datetime,
    ):
        inventory_path, lead_log_path = paths
        with pytest.raises(ApprovalError, match="attestation"):
            approve_lead(
                lead_id="lead-closed-001",
                niche="warmtepomp",
                region_nl="utrecht|amersfoort",
                intent_strength="WARM",
                captured_at=captured_at,
                source_class="burner_closed",
                reviewer_name="sem",
                decay_windows=decay_windows,
                inventory_path=inventory_path,
                lead_log_path=lead_log_path,
                reviewer_attestation="",
            )
        assert not inventory_path.exists() or _row_count(inventory_path) == 0
        assert not lead_log_path.exists() or _row_count(lead_log_path) == 0

    def test_closed_group_with_attestation_ok(
        self,
        paths: tuple[Path, Path],
        decay_windows: dict[str, dict[str, int]],
        captured_at: datetime,
    ):
        inventory_path, lead_log_path = paths
        approve_lead(
            lead_id="lead-closed-002",
            niche="zonnepanelen",
            region_nl="utrecht|utrecht",
            intent_strength="HOT",
            captured_at=captured_at,
            source_class="burner_closed",
            reviewer_name="sem",
            decay_windows=decay_windows,
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
            reviewer_attestation="Lid van groep sinds 2024; observerend account",
        )
        with inventory_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["source_class"] == "burner_closed"
        assert rows[0]["reviewer_attestation"].startswith("Lid van groep")

    def test_apify_public_no_attestation_required(
        self,
        paths: tuple[Path, Path],
        decay_windows: dict[str, dict[str, int]],
        captured_at: datetime,
    ):
        inventory_path, lead_log_path = paths
        approve_lead(
            lead_id="lead-pub-001",
            niche="zonnepanelen",
            region_nl="utrecht|amersfoort",
            intent_strength="WARM",
            captured_at=captured_at,
            source_class="apify_public",
            reviewer_name="sem",
            decay_windows=decay_windows,
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
        )
        with inventory_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["reviewer_attestation"] == ""

    def test_unknown_niche_raises(
        self,
        paths: tuple[Path, Path],
        decay_windows: dict[str, dict[str, int]],
        captured_at: datetime,
    ):
        inventory_path, lead_log_path = paths
        with pytest.raises(KeyError, match="laadpaal"):
            approve_lead(
                lead_id="lead-unknown-001",
                niche="laadpaal",
                region_nl="utrecht|amersfoort",
                intent_strength="HOT",
                captured_at=captured_at,
                source_class="apify_public",
                reviewer_name="sem",
                decay_windows=decay_windows,
                inventory_path=inventory_path,
                lead_log_path=lead_log_path,
            )

    def test_returns_inventory_row_dict(
        self,
        paths: tuple[Path, Path],
        decay_windows: dict[str, dict[str, int]],
        captured_at: datetime,
    ):
        inventory_path, lead_log_path = paths
        result = approve_lead(
            lead_id="lead-ret-001",
            niche="warmtepomp",
            region_nl="utrecht|amersfoort",
            intent_strength="HOT",
            captured_at=captured_at,
            source_class="apify_public",
            reviewer_name="sem",
            decay_windows=decay_windows,
            inventory_path=inventory_path,
            lead_log_path=lead_log_path,
        )
        expected_keys = {
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
        }
        assert set(result.keys()) == expected_keys
        assert result["lead_id"] == "lead-ret-001"
        assert result["niche"] == "warmtepomp"
        assert result["intent_strength"] == "HOT"
        assert result["source_class"] == "apify_public"
        assert result["captured_at"].startswith("2026-05-19")
        assert result["expires_at"].startswith("2026-05-26")


def _row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.DictReader(f))
