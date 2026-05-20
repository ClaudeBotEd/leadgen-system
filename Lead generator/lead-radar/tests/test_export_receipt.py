"""Tests for exporting one real reviewed lead receipt."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from run_export_receipt import export_receipt, load_reviewed_lead


UTC = timezone.utc
NOW = datetime(2026, 5, 20, 10, 0, 0, tzinfo=UTC)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _write_installers(path: Path) -> None:
    path.write_text(
        "installer_id,company_name,contact_name,email,phone,city,regions,niches,active,notes\n"
        "I-001,Visser Installaties,Jeroen Visser,jeroen@visser.test,,Amsterdam,Amsterdam,warmtepomp,true,\n",
        encoding="utf-8",
    )


def _reviewed_lead(**overrides: object) -> dict:
    lead = {
        "lead_id": "L-REAL-001",
        "snippet": "Ik zoek een installateur in regio Amsterdam voor een warmtepomp.",
        "source_url": "https://tweakers.net/threads/real-1",
        "source_platform": "tweakers",
        "captured_at": (NOW - timedelta(hours=4)).isoformat(),
        "region": "Amsterdam",
        "niche": "warmtepomp",
        "confidence_band": "HOT",
        "band_reason": "Expliciete installateurvraag met regio.",
        "reviewer_name": "Marieke de Vries",
        "reviewer_email": "marieke@lead-radar.nl",
        "reviewed_at": (NOW - timedelta(hours=2)).isoformat(),
    }
    lead.update(overrides)
    return lead


def test_export_receipt_writes_html_from_reviewed_jsonl(tmp_path: Path) -> None:
    input_path = tmp_path / "approved.jsonl"
    installers_path = tmp_path / "installers.csv"
    lead_log_path = tmp_path / "lead_log.csv"
    output_path = tmp_path / "receipts" / "L-REAL-001.html"

    _write_jsonl(input_path, [_reviewed_lead()])
    _write_installers(installers_path)
    lead_log_path.write_text("at,lead_id,from_state,to_state,actor,reason\n", encoding="utf-8")

    written = export_receipt(
        input_path=input_path,
        lead_id="L-REAL-001",
        output_path=output_path,
        installers_path=installers_path,
        lead_log_path=lead_log_path,
        now=NOW,
    )

    assert written == output_path
    html = output_path.read_text(encoding="utf-8")
    assert "Ik zoek een installateur in regio Amsterdam voor een warmtepomp." in html
    assert 'href="https://tweakers.net/threads/real-1"' in html
    assert "LR-2026-05-20-0001" in html
    assert "demo-receipt-sample" not in html
    assert "Voorbeeld Installatie BV" not in html


def test_load_reviewed_lead_requires_matching_lead_id(tmp_path: Path) -> None:
    input_path = tmp_path / "approved.jsonl"
    _write_jsonl(input_path, [_reviewed_lead()])

    with pytest.raises(ValueError, match="not found"):
        load_reviewed_lead(input_path, "missing")
