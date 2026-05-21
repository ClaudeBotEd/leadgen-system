import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

UTC = timezone.utc


@pytest.fixture
def env_setup(tmp_path: Path, monkeypatch):
    reviewed = tmp_path / "reviewed.jsonl"
    installers = tmp_path / "installers.csv"
    log = tmp_path / "lead_log.csv"
    audit = tmp_path / "delivery_log.jsonl"
    reviewed.write_text(
        json.dumps(
            {
                "lead_id": "L-001",
                "snippet": "Ik zoek een installateur voor warmtepomp.",
                "source_url": "https://tweakers.net/p/1",
                "source_platform": "tweakers",
                "captured_at": datetime(2026, 5, 18, 10, tzinfo=UTC).isoformat(),
                "region": "Amsterdam",
                "niche": "warmtepomp",
                "confidence_band": "HOT",
                "band_reason": "Expliciet budget en tijdshorizon.",
                "reviewer_name": "Marieke de Vries",
                "reviewer_email": "marieke@lead-radar.nl",
                "reviewed_at": datetime(2026, 5, 18, 12, tzinfo=UTC).isoformat(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    installers.write_text(
        "installer_id,company_name,contact_name,email,phone,city,regions,niches,active,notes\n"
        "I-001,Visser,Jeroen Visser,jeroen@x.nl,,Amsterdam,Amsterdam,warmtepomp,true,\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DELIVERY_REPLY_DOMAIN", "lead-radar.nl")
    monkeypatch.setenv("DELIVERY_DRY_RUN", "true")
    monkeypatch.setenv("DELIVERY_INPUT_PATH", str(reviewed))
    monkeypatch.setenv("DELIVERY_INSTALLERS_PATH", str(installers))
    monkeypatch.setenv("DELIVERY_LOG_PATH", str(log))
    monkeypatch.setenv("DELIVERY_AUDIT_PATH", str(audit))
    return {"audit": audit, "log": log}


def test_cli_dispatch_subcommand_runs(env_setup, monkeypatch, capsys):
    from delivery.cli import main

    monkeypatch.setattr(sys, "argv", ["delivery", "dispatch", "--limit", "1"])
    rc = main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "delivered=1" in out
    assert env_setup["audit"].exists()


def test_cli_help_lists_dispatch(monkeypatch, capsys):
    from delivery.cli import main

    monkeypatch.setattr(sys, "argv", ["delivery", "--help"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "dispatch" in captured
