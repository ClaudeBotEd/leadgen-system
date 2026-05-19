import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from delivery.config import DeliveryConfig
from delivery.dispatcher import DispatchSummary, dispatch

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def write_approved(path: Path, leads):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for lead in leads:
            f.write(json.dumps(lead) + "\n")


def write_installers(path: Path, rows):
    header = "installer_id,company_name,contact_name,email,phone,city,regions,niches,active,notes\n"
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")


def base_lead(**overrides):
    base = dict(
        lead_id="L-001",
        snippet="Ik zoek een installateur voor warmtepomp + buffervat.",
        source_url="https://tweakers.net/threads/12345",
        source_platform="tweakers",
        captured_at=(NOW - timedelta(hours=4)).isoformat(),
        region="Amsterdam",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="Expliciet budget en tijdshorizon.",
        reviewer_name="Marieke de Vries",
        reviewer_email="marieke@lead-radar.nl",
        reviewed_at=(NOW - timedelta(hours=2)).isoformat(),
    )
    base.update(overrides)
    return base


@pytest.fixture
def config(tmp_path: Path):
    return DeliveryConfig(
        reply_domain="lead-radar.nl",
        dry_run=True,
        smtp_host=None,
        smtp_user=None,
        smtp_password=None,
        decay_days=8,
        input_path=tmp_path / "reviewed.jsonl",
        installers_path=tmp_path / "installers.csv",
        log_path=tmp_path / "lead_log.csv",
        audit_path=tmp_path / "delivery_log.jsonl",
    )


def test_dispatch_dry_run_routes_and_audits(config):
    write_approved(config.input_path, [base_lead()])
    write_installers(
        config.installers_path,
        [
            "I-001,Visser,Jeroen Visser,jeroen@visserinstallaties.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        ],
    )
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert isinstance(summary, DispatchSummary)
    assert summary.total == 1 and summary.delivered == 1
    audit_lines = config.audit_path.read_text(encoding="utf-8").strip().splitlines()
    row = json.loads(audit_lines[0])
    assert row["status"] == "delivered"
    assert row["case_id"].startswith("LR-2026-05-18-")
    assert row["installer_email"] == "jeroen@visserinstallaties.nl"
    assert row["dry_run"] is True


def test_dispatch_writes_pcs_transition_when_not_dry_run(config, monkeypatch):
    config.dry_run = False
    config.smtp_host = "smtp.x"
    config.smtp_user = "marieke@lead-radar.nl"
    config.smtp_password = "x"
    write_approved(config.input_path, [base_lead()])
    write_installers(
        config.installers_path,
        [
            "I-001,Visser,Jeroen Visser,jeroen@visserinstallaties.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        ],
    )
    sent = {"count": 0}
    monkeypatch.setattr(
        "delivery.dispatcher.send_smtp",
        lambda msg, cfg: (sent.__setitem__("count", sent["count"] + 1) or "msg-1"),
    )
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert summary.delivered == 1 and sent["count"] == 1
    log_text = config.log_path.read_text(encoding="utf-8")
    assert "DELIVERED" in log_text and "L-001" in log_text


def test_dispatch_skips_when_no_installer_match(config):
    write_approved(config.input_path, [base_lead(region="Groningen")])
    write_installers(
        config.installers_path,
        [
            "I-001,Visser,Jeroen,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        ],
    )
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert summary.delivered == 0 and summary.unrouted == 1
    audit_row = json.loads(config.audit_path.read_text(encoding="utf-8").strip())
    assert audit_row["status"] == "unrouted"


def test_dispatch_skips_when_vocab_violation(config):
    lead = base_lead(band_reason="qualified lead from Amsterdam")
    write_approved(config.input_path, [lead])
    write_installers(
        config.installers_path,
        [
            "I-001,Visser,Jeroen,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        ],
    )
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert summary.delivered == 0 and summary.vocab_violations == 1


def test_dispatch_respects_exclusivity_via_log(config):
    write_approved(config.input_path, [base_lead(lead_id="L-001")])
    write_installers(
        config.installers_path,
        [
            "I-001,Visser,Jeroen,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        ],
    )
    config.log_path.parent.mkdir(parents=True, exist_ok=True)
    config.log_path.write_text(
        "at,lead_id,from_state,to_state,actor,reason\n"
        "2026-05-17T08:00:00+00:00,L-001,APPROVED,DELIVERED,m@x,prior\n",
        encoding="utf-8",
    )
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config)
    assert summary.delivered == 0 and summary.unrouted == 1


def test_dispatch_respects_limit(config):
    leads = [base_lead(lead_id=f"L-{i:03d}") for i in range(5)]
    write_approved(config.input_path, leads)
    write_installers(
        config.installers_path,
        [
            "I-001,Visser,Jeroen,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        ],
    )
    with patch("delivery.dispatcher._now", return_value=NOW):
        summary = dispatch(config, limit=2)
    assert summary.total == 2 and summary.delivered == 2
