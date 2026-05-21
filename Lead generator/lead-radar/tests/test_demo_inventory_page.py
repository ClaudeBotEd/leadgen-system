"""Unit tests for demo_bundle.inventory_page."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from consumer.inventory import append_inventory_row
from demo_bundle.inventory_page import render_inventory_html


@pytest.fixture
def filled_inventory(tmp_path: Path) -> Path:
    path = tmp_path / "lead_inventory.csv"
    now = datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc)
    append_inventory_row(
        path,
        lead_id="demo-001",
        niche="warmtepomp",
        region_nl="utrecht|amersfoort",
        intent_strength="HOT",
        captured_at=(now - timedelta(hours=6)).isoformat(timespec="seconds"),
        approved_at=(now - timedelta(hours=5)).isoformat(timespec="seconds"),
        expires_at=(now + timedelta(days=14)).isoformat(timespec="seconds"),
        source_class="apify_public",
    )
    append_inventory_row(
        path,
        lead_id="demo-002",
        niche="zonnepanelen",
        region_nl="utrecht|utrecht",
        intent_strength="WARM",
        captured_at=(now - timedelta(days=3)).isoformat(timespec="seconds"),
        approved_at=(now - timedelta(days=3)).isoformat(timespec="seconds"),
        expires_at=(now + timedelta(days=25)).isoformat(timespec="seconds"),
        source_class="burner_closed",
        reviewer_attestation="Lid sinds 2024",
    )
    return path


class TestRenderInventoryHtml:
    def test_contains_header_and_lead_ids(self, filled_inventory: Path):
        html = render_inventory_html(
            inventory_path=filled_inventory,
            snapshot_at=datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc),
        )
        assert "<html" in html.lower()
        assert "Lead-radar" in html
        assert "demo-001" in html
        assert "demo-002" in html
        assert "warmtepomp" in html
        assert "HOT" in html and "WARM" in html

    def test_escapes_html_in_attestation(self, tmp_path: Path):
        path = tmp_path / "lead_inventory.csv"
        now = datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc)
        append_inventory_row(
            path,
            lead_id="demo-xss",
            niche="warmtepomp",
            region_nl="utrecht|amersfoort",
            intent_strength="HOT",
            captured_at=now.isoformat(timespec="seconds"),
            approved_at=now.isoformat(timespec="seconds"),
            expires_at=(now + timedelta(days=14)).isoformat(timespec="seconds"),
            source_class="burner_closed",
            reviewer_attestation="<script>alert('x')</script>",
        )
        html = render_inventory_html(
            inventory_path=path,
            snapshot_at=now,
        )
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_empty_inventory_renders_placeholder(self, tmp_path: Path):
        path = tmp_path / "lead_inventory.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write(
                "lead_id,niche,region_nl,intent_strength,captured_at,"
                "approved_at,expires_at,source_class,reviewer_attestation,"
                "delivered_to,demo_used_at,still_warm_checked_at\n"
            )
        html = render_inventory_html(
            inventory_path=path,
            snapshot_at=datetime(2026, 5, 19, 9, 0, 0, tzinfo=timezone.utc),
        )
        assert "Geen leads" in html or "Pool is leeg" in html
