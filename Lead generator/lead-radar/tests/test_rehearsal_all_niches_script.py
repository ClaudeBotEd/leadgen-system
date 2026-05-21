from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_rehearsal_all_niches.sh"
WARMTEPOMP_SCRIPT = ROOT / "scripts" / "run_rehearsal_warmtepomp.sh"


def _script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_full_rehearsal_script_exists_and_is_executable() -> None:
    assert SCRIPT.exists()
    assert SCRIPT.stat().st_mode & stat.S_IXUSR


def test_full_rehearsal_script_is_bash_with_strict_mode() -> None:
    text = _script_text()

    assert text.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in text


def test_full_rehearsal_script_requires_rehearsal_sheet_id() -> None:
    text = _script_text()

    assert "LEAD_RADAR_REHEARSAL_SPREADSHEET_ID" in text
    assert '[[ -z "${LEAD_RADAR_REHEARSAL_SPREADSHEET_ID:-}" ]]' in text
    assert "missing LEAD_RADAR_REHEARSAL_SPREADSHEET_ID" in text
    assert re.search(r"LEAD_RADAR_REHEARSAL_SPREADSHEET_ID[\s\S]+exit 1", text)


def test_full_rehearsal_script_checks_credentials_and_anthropic_warning() -> None:
    text = _script_text()

    assert '.credentials/google_sheets.json' in text
    assert '[[ ! -f "$CREDENTIALS" ]]' in text
    assert "ANTHROPIC_API_KEY" in text
    assert "WARNING: ANTHROPIC_API_KEY is missing" in text
    assert "sleep 3" in text


def test_full_rehearsal_script_sets_timestamp_outroot_and_env() -> None:
    text = _script_text()

    assert 'TIMESTAMP="$(date +%Y-%m-%dT%H-%M-%S)"' in text
    assert 'full_rehearsal_${TIMESTAMP}' in text
    assert 'LEAD_RADAR_SPREADSHEET_ID="$LEAD_RADAR_REHEARSAL_SPREADSHEET_ID"' in text
    assert "LEAD_RADAR_SHEETS_OPP_FLOOR=40" in text
    assert "LEAD_RADAR_LLM_BUDGET_EUR=3.00" in text


def test_full_rehearsal_script_resolves_niches_and_sources_dynamically() -> None:
    text = _script_text()

    assert "yaml.safe_load" in text
    assert "consumer/queries.yaml" in text
    assert "PROOF_SPRINT_SOURCES" in text
    assert "python3" in text
    assert not re.search(r"(?<![A-Za-z0-9_])python\s", text)


def test_full_rehearsal_script_uses_expected_consumer_flags() -> None:
    text = _script_text()

    assert "python3 run_consumer.py" in text
    assert '--niche "$niche"' in text
    assert '--sources "$SOURCES"' in text
    assert "--max-age-days 14" in text
    assert "--sheets" in text
    assert "--no-telegram" in text
    assert "--no-llm" not in text
    assert "--daily" not in text
    assert "--no-sheets" not in text


def test_full_rehearsal_script_records_exit_codes_and_summarizes() -> None:
    text = _script_text()

    assert 'PIPESTATUS[0]' in text
    assert '> "$NICHE_DIR/.exit_code"' in text
    assert 'scripts/summarize_rehearsal_results.py "$OUTROOT"' in text
    assert 'Summary: $OUTROOT/summary.md' in text
    assert 'Machine summary: $OUTROOT/summary.json' in text
    assert re.search(r"exit 0\s*$", text)


def test_full_rehearsal_script_missing_sheet_id_exits_before_consumer() -> None:
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
    assert "Running niche:" not in combined
    assert "run_consumer.py" not in combined


def test_original_warmtepomp_rehearsal_script_is_unchanged() -> None:
    assert WARMTEPOMP_SCRIPT.exists()

    diff = subprocess.run(
        ["git", "diff", "--", "scripts/run_rehearsal_warmtepomp.sh"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "scripts/run_rehearsal_warmtepomp.sh"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert diff.stdout == ""
    assert status.stdout == ""
