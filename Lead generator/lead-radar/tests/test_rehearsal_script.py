from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_rehearsal_warmtepomp.sh"
METRICS = ROOT / "data" / "proof_sprint_2026-05-20" / "metrics.md"
OUTDIR = ROOT / "data" / "proof_sprint_2026-05-20" / "consumer" / "rehearsal_warmtepomp"


def _script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_rehearsal_script_exists_and_is_executable() -> None:
    assert SCRIPT.exists()
    mode = SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR


def test_rehearsal_script_bash_syntax() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], cwd=ROOT, check=True)


def test_rehearsal_script_sets_required_env_overrides() -> None:
    text = _script_text()

    assert "LEAD_RADAR_SHEETS_OPP_FLOOR=40" in text
    assert "LEAD_RADAR_LLM_BUDGET_EUR=3.00" in text
    assert 'LEAD_RADAR_SPREADSHEET_ID="$LEAD_RADAR_REHEARSAL_SPREADSHEET_ID"' in text


def test_rehearsal_script_resolves_canonical_sources_with_python3() -> None:
    text = _script_text()

    assert "PROOF_SPRINT_SOURCES" in text
    assert "python3 -c" in text
    assert "python3 run_consumer.py" in text
    assert not re.search(r"(?<![A-Za-z0-9_])python\s", text)


def test_rehearsal_script_uses_expected_consumer_flags() -> None:
    text = _script_text()

    assert "--niche warmtepomp" in text
    assert '--sources "$CANONICAL_SOURCES"' in text
    assert "--max-age-days 14" in text
    assert "--sheets" in text
    assert "--no-telegram" in text
    assert "--no-sheets" not in text


def test_rehearsal_script_writes_to_rehearsal_outdir() -> None:
    text = _script_text()

    assert "rehearsal_warmtepomp" in text
    assert 'tee "$OUTDIR/run.log"' in text


def test_rehearsal_script_requires_rehearsal_spreadsheet_id() -> None:
    text = _script_text()

    assert "LEAD_RADAR_REHEARSAL_SPREADSHEET_ID" in text
    assert '[[ -z "${LEAD_RADAR_REHEARSAL_SPREADSHEET_ID:-}" ]]' in text


def test_rehearsal_script_missing_sheet_id_exits_before_consumer() -> None:
    env = os.environ.copy()
    env.pop("LEAD_RADAR_REHEARSAL_SPREADSHEET_ID", None)
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 1
    assert "missing LEAD_RADAR_REHEARSAL_SPREADSHEET_ID" in combined
    assert "Running warmtepomp official proof-sprint rehearsal" not in combined


def test_metrics_contains_rehearsal_section() -> None:
    text = METRICS.read_text(encoding="utf-8")

    assert "## Rehearsal Run — warmtepomp" in text
    assert "| rehearsal_warmtepomp |" in text
    assert "OPP (40-59)" in text


def test_rehearsal_outdir_gitkeep_exists() -> None:
    assert (OUTDIR / ".gitkeep").exists()
