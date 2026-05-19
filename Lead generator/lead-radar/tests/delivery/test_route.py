from datetime import datetime, timedelta, timezone
from pathlib import Path

from delivery.model import ReviewedLead
from delivery.route import load_installers, pick_installer

UTC = timezone.utc
NOW = datetime(2026, 5, 18, 14, 0, 0, tzinfo=UTC)


def make_rl(**overrides):
    base = dict(
        lead_id="L-001",
        snippet="x",
        source_url="https://x.example/p",
        source_platform="tweakers",
        captured_at=NOW - timedelta(hours=4),
        region="Amsterdam",
        niche="warmtepomp",
        confidence_band="HOT",
        band_reason="r",
        reviewer_name="M de Vries",
        reviewer_email="m@x.nl",
        reviewed_at=NOW - timedelta(hours=2),
    )
    base.update(overrides)
    return ReviewedLead(**base)


def _write_installers(tmp_path: Path, rows):
    p = tmp_path / "installers.csv"
    header = "installer_id,company_name,contact_name,email,phone,city,regions,niches,active,notes\n"
    p.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return p


def _write_log(tmp_path: Path, lines):
    p = tmp_path / "lead_log.csv"
    header = "at,lead_id,from_state,to_state,actor,reason\n"
    p.write_text(header + "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return p


def test_load_installers_parses_pipe_separated_lists(tmp_path):
    csv = _write_installers(
        tmp_path,
        [
            "I-001,Visser,Jeroen Visser,j@v.nl,,Amsterdam,Amsterdam|Haarlem,warmtepomp|airco,true,",
        ],
    )
    installers = load_installers(csv)
    assert installers[0].regions == ["Amsterdam", "Haarlem"]
    assert installers[0].niches == ["warmtepomp", "airco"]


def test_picks_first_active_match(tmp_path):
    csv = _write_installers(
        tmp_path,
        [
            "I-001,Visser,J,j@v.nl,,Amsterdam,Utrecht,warmtepomp,true,",
            "I-002,Bakker,B,b@b.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
            "I-003,Klaas,K,k@k.nl,,Amsterdam,Amsterdam,airco,true,",
        ],
    )
    log = _write_log(tmp_path, [])
    picked = pick_installer(make_rl(), load_installers(csv), log_path=log)
    assert picked is not None and picked.installer_id == "I-002"


def test_skips_inactive(tmp_path):
    csv = _write_installers(
        tmp_path,
        [
            "I-001,Visser,J,j@v.nl,,Amsterdam,Amsterdam,warmtepomp,false,",
            "I-002,Bakker,B,b@b.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        ],
    )
    log = _write_log(tmp_path, [])
    picked = pick_installer(make_rl(), load_installers(csv), log_path=log)
    assert picked.installer_id == "I-002"


def test_returns_none_when_no_match(tmp_path):
    csv = _write_installers(
        tmp_path,
        [
            "I-001,Visser,J,j@v.nl,,Rotterdam,Rotterdam,warmtepomp,true,",
        ],
    )
    log = _write_log(tmp_path, [])
    assert pick_installer(make_rl(), load_installers(csv), log_path=log) is None


def test_respects_exclusivity_already_delivered(tmp_path):
    csv = _write_installers(
        tmp_path,
        [
            "I-001,Visser,J,j@v.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        ],
    )
    log = _write_log(
        tmp_path,
        [
            "2026-05-17T08:00:00+00:00,L-001,APPROVED,DELIVERED,m@x,prior",
        ],
    )
    picked = pick_installer(make_rl(lead_id="L-001"), load_installers(csv), log_path=log)
    assert picked is None


def test_missing_log_treated_as_empty(tmp_path):
    csv = _write_installers(
        tmp_path,
        [
            "I-001,Visser,J,j@v.nl,,Amsterdam,Amsterdam,warmtepomp,true,",
        ],
    )
    picked = pick_installer(make_rl(), load_installers(csv), log_path=tmp_path / "does-not-exist.csv")
    assert picked is not None
