from __future__ import annotations

import csv
from pathlib import Path

import pytest

from output.exporter import CSV_COLUMNS, append_to_master
from pcs import (
    INSTALLERS_FIELDS,
    LEAD_LOG_FIELDS,
    append_transition,
    deliver_lead,
    ensure_leads_master_workflow,
    load_installers,
    normalize_state,
    reject_lead,
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_leads_master_columns_include_pcs_workflow_fields(tmp_path: Path) -> None:
    master = tmp_path / "leads_master.csv"
    append_to_master([{"lead_id": "lr_1", "company_name": "Test BV"}], master_path=master)

    with master.open("r", encoding="utf-8", newline="") as f:
        header = next(csv.reader(f))

    assert header == CSV_COLUMNS
    assert header[-3:] == ["assigned_to", "sent_at", "state"]
    assert read_rows(master)[0]["state"] == "NEW"


def test_ensure_leads_master_workflow_extends_existing_csv(tmp_path: Path) -> None:
    master = tmp_path / "leads_master.csv"
    master.write_text("lead_id,company_name\nlr_1,Test BV\n", encoding="utf-8")

    ensure_leads_master_workflow(master)

    rows = read_rows(master)
    assert rows == [{
        "lead_id": "lr_1",
        "company_name": "Test BV",
        "assigned_to": "",
        "sent_at": "",
        "state": "NEW",
    }]


def test_append_transition_is_append_only_and_writes_one_row_per_call(tmp_path: Path) -> None:
    log = tmp_path / "lead_log.csv"

    append_transition("lr_1", "NEW", "APPROVED", actor="founder", reason="qualified", log_path=log, at="t1")
    append_transition("lr_1", "APPROVED", "DELIVERED", actor="founder", reason="sent", log_path=log, at="t2")

    with log.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == LEAD_LOG_FIELDS
        rows = list(reader)

    assert [row["to_state"] for row in rows] == ["APPROVED", "DELIVERED"]
    assert rows[0] == {
        "at": "t1",
        "lead_id": "lr_1",
        "from_state": "NEW",
        "to_state": "APPROVED",
        "actor": "founder",
        "reason": "qualified",
    }


def test_append_transition_refuses_bad_log_header(tmp_path: Path) -> None:
    log = tmp_path / "lead_log.csv"
    log.write_text("lead_id,state\nlr_1,NEW\n", encoding="utf-8")

    with pytest.raises(ValueError, match="header mismatch"):
        append_transition("lr_1", "NEW", "APPROVED", actor="founder", reason="qualified", log_path=log)


def test_transition_helpers_update_master_and_append_log(tmp_path: Path) -> None:
    master = tmp_path / "leads_master.csv"
    log = tmp_path / "lead_log.csv"
    master.write_text("lead_id,company_name\nlr_1,Test BV\n", encoding="utf-8")

    delivered = deliver_lead(
        "lr_1",
        actor="founder",
        reason="pilot delivery",
        assigned_to="inst_1",
        sent_at="2026-05-18T10:00:00+00:00",
        master_path=master,
        log_path=log,
    )

    assert delivered["state"] == "DELIVERED"
    assert delivered["assigned_to"] == "inst_1"
    assert read_rows(master)[0]["sent_at"] == "2026-05-18T10:00:00+00:00"
    assert read_rows(log)[0]["from_state"] == "NEW"
    assert read_rows(log)[0]["to_state"] == "DELIVERED"


def test_reject_lead_uses_only_allowed_states(tmp_path: Path) -> None:
    master = tmp_path / "leads_master.csv"
    log = tmp_path / "lead_log.csv"
    master.write_text("lead_id,state\nlr_1,APPROVED\n", encoding="utf-8")

    row = reject_lead("lr_1", actor="founder", reason="bad fit", master_path=master, log_path=log)

    assert row["state"] == "REJECTED"
    with pytest.raises(ValueError):
        normalize_state("FOLLOWUP")


def test_installers_loader_creates_schema_and_loads_plain_dicts(tmp_path: Path) -> None:
    installers = tmp_path / "installers.csv"

    assert load_installers(installers) == []
    with installers.open("r", encoding="utf-8", newline="") as f:
        assert next(csv.reader(f)) == INSTALLERS_FIELDS

    installers.write_text(
        "installer_id,company_name,contact_name,email,phone,city,regions,niches,active,notes\n"
        "inst_1,InstallCo,Ada,ada@example.test,06123,Utrecht,Utrecht,warmtepomp,yes,pilot\n",
        encoding="utf-8",
    )

    assert load_installers(installers) == [{
        "installer_id": "inst_1",
        "company_name": "InstallCo",
        "contact_name": "Ada",
        "email": "ada@example.test",
        "phone": "06123",
        "city": "Utrecht",
        "regions": "Utrecht",
        "niches": "warmtepomp",
        "active": "yes",
        "notes": "pilot",
    }]
