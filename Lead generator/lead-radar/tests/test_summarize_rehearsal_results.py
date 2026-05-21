from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest

from scripts.summarize_rehearsal_results import summarize_outroot


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_rehearsal_results.py"


def _make_outroot(tmp_path: Path) -> Path:
    outroot = tmp_path / "full_rehearsal_2026-05-21T10-11-12"
    outroot.mkdir()
    return outroot


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = ["id", "score", "url", "title"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_niche(
    outroot: Path,
    niche: str,
    *,
    exit_code: int | None = 0,
    csv_rows: list[dict[str, object]] | None = None,
    json_leads: list[dict[str, object]] | str | None = None,
    log: str | None = "",
) -> Path:
    niche_dir = outroot / niche
    niche_dir.mkdir()
    if exit_code is not None:
        (niche_dir / ".exit_code").write_text(f"{exit_code}\n", encoding="utf-8")
    if log is not None:
        (niche_dir / "run.log").write_text(log, encoding="utf-8")
    if csv_rows is not None:
        _write_csv(niche_dir / f"leads_{niche}_2026-05-21.csv", csv_rows)
    if json_leads is not None:
        payload = json_leads if isinstance(json_leads, str) else json.dumps(json_leads)
        (niche_dir / f"leads_{niche}_2026-05-21.json").write_text(
            payload,
            encoding="utf-8",
        )
    return niche_dir


def _run_summary(outroot: Path) -> dict:
    summary = summarize_outroot(outroot)
    assert (outroot / "summary.md").exists()
    assert (outroot / "summary.json").exists()
    return summary


def test_exit_zero_with_csv_and_json_leads_is_pass(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(
        outroot,
        "warmtepomp",
        csv_rows=[{"id": "a", "score": 81, "url": "https://x/a", "title": "A"}],
        json_leads=[{"id": "a", "score": 81, "url": "https://x/a", "title": "A"}],
        log=(
            "[warmtepomp] raw=10 -> leads=1 (promo=2 oud=3 low=4 no_ts=0 "
            "hardblock=1 fuzzy=0 llm_calls=5 cost=EUR0.0123 author_calls=0)\n"
            "                  sheets HOT +1  ALL +1  OPP +0\n"
        ),
    )

    niche = _run_summary(outroot)["niches"][0]

    assert niche["status"] == "PASS"
    assert niche["csv_row_count"] == 1
    assert niche["counts"]["raw"] == 10
    assert niche["llm_calls"]["total"] == 5
    assert niche["llm_calls"]["api"] == 5
    assert niche["llm_calls"]["cost_eur"] == pytest.approx(0.0123)
    assert niche["sheets_writes"] == {"hot": 1, "all": 1, "opp": 0}


def test_exit_zero_with_no_leads_is_warn(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(outroot, "airco", csv_rows=[], json_leads=[])

    niche = _run_summary(outroot)["niches"][0]

    assert niche["status"] == "WARN"
    assert niche["csv_row_count"] == 0


def test_nonzero_exit_is_fail(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(
        outroot,
        "cv",
        exit_code=1,
        csv_rows=[{"id": "a", "score": 75, "url": "https://x/a", "title": "A"}],
        json_leads=[{"id": "a", "score": 75, "url": "https://x/a", "title": "A"}],
    )

    niche = _run_summary(outroot)["niches"][0]

    assert niche["status"] == "FAIL"
    assert niche["exit_code"] == 1


def test_missing_exit_code_is_fail_and_marked_missing(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(
        outroot,
        "isolatie",
        exit_code=None,
        csv_rows=[{"id": "a", "score": 75, "url": "https://x/a", "title": "A"}],
        json_leads=[{"id": "a", "score": 75, "url": "https://x/a", "title": "A"}],
    )

    niche = _run_summary(outroot)["niches"][0]

    assert niche["status"] == "FAIL"
    assert niche["exit_code"] is None
    assert niche["exit_code_raw"] == "MISSING"


def test_summary_json_has_required_top_level_keys(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(outroot, "ventilatie", csv_rows=[], json_leads=[])

    _run_summary(outroot)
    payload = json.loads((outroot / "summary.json").read_text(encoding="utf-8"))

    assert {"timestamp", "outroot", "env", "niches", "aggregate"} <= payload.keys()


def test_top_leads_are_sorted_by_score_desc(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(
        outroot,
        "zonnepanelen",
        csv_rows=[
            {"id": "low", "score": 45, "url": "https://x/low", "title": "Low"},
            {"id": "high", "score": 90, "url": "https://x/high", "title": "High"},
            {"id": "mid", "score": 72, "url": "https://x/mid", "title": "Mid"},
        ],
        json_leads=[
            {"id": "low", "score": 45, "url": "https://x/low", "title": "Low"},
            {"id": "high", "score": 90, "url": "https://x/high", "title": "High"},
            {"id": "mid", "score": 72, "url": "https://x/mid", "title": "Mid"},
        ],
    )

    niche = _run_summary(outroot)["niches"][0]

    assert [lead["id"] for lead in niche["top_leads"]] == ["high", "mid", "low"]


def test_receipt_candidates_only_include_score_70_plus(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(
        outroot,
        "laadpaal",
        csv_rows=[
            {"id": "cold", "score": 69, "url": "https://x/cold", "title": "Cold"},
            {"id": "warm", "score": 70, "url": "https://x/warm", "title": "Warm"},
        ],
        json_leads=[
            {"id": "cold", "score": 69, "url": "https://x/cold", "title": "Cold"},
            {"id": "warm", "score": 70, "url": "https://x/warm", "title": "Warm"},
        ],
    )

    summary = _run_summary(outroot)
    niche = summary["niches"][0]
    markdown = (outroot / "summary.md").read_text(encoding="utf-8")

    assert [lead["id"] for lead in niche["receipt_candidates"]] == ["warm"]
    assert "Receipt export requires approved JSONL + lead_id via run_export_receipt.py." in markdown
    assert "warm" in markdown
    assert "cold" not in markdown.split("## Receipt Candidates", maxsplit=1)[1]


def test_aggregate_totals_add_up(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(
        outroot,
        "dakwerk",
        csv_rows=[
            {"id": "a", "score": 80, "url": "https://x/a", "title": "A"},
            {"id": "b", "score": 65, "url": "https://x/b", "title": "B"},
        ],
        json_leads=[
            {"id": "a", "score": 80, "url": "https://x/a", "title": "A"},
            {"id": "b", "score": 65, "url": "https://x/b", "title": "B"},
        ],
        log="llm_calls total=4 api=3 cache=1 cost=EUR0.1000\nsheets HOT +1  ALL +2  OPP +3\n",
    )
    _write_niche(
        outroot,
        "kozijnen",
        csv_rows=[{"id": "c", "score": 72, "url": "https://x/c", "title": "C"}],
        json_leads=[{"id": "c", "score": 72, "url": "https://x/c", "title": "C"}],
        log="llm_calls total=2 api=2 cache=0 cost=EUR0.0500\nsheets HOT +0  ALL +1  OPP +1\n",
    )

    aggregate = _run_summary(outroot)["aggregate"]

    assert aggregate["total_leads"] == 3
    assert aggregate["llm_calls"] == {
        "total": 6,
        "api": 5,
        "cache": 1,
        "cost_eur": 0.15,
    }
    assert aggregate["sheets_writes"] == {"hot": 1, "all": 3, "opp": 4, "total": 8}
    assert aggregate["status_counts"] == {"PASS": 2, "WARN": 0, "FAIL": 0}


def test_missing_run_log_does_not_crash(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(
        outroot,
        "renovatie",
        csv_rows=[{"id": "a", "score": 75, "url": "https://x/a", "title": "A"}],
        json_leads=[{"id": "a", "score": 75, "url": "https://x/a", "title": "A"}],
        log=None,
    )

    niche = _run_summary(outroot)["niches"][0]

    assert niche["status"] == "PASS"
    assert niche["run_log_present"] is False
    assert niche["error_count"] == 0


def test_malformed_json_does_not_crash(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(
        outroot,
        "vloerverwarming",
        csv_rows=[{"id": "a", "score": 75, "url": "https://x/a", "title": "A"}],
        json_leads="{not json",
    )

    niche = _run_summary(outroot)["niches"][0]

    assert niche["status"] == "PASS"
    assert niche["json_malformed"] is True
    assert niche["top_leads"] == []


def test_summarizer_cli_writes_summary_files(tmp_path: Path) -> None:
    outroot = _make_outroot(tmp_path)
    _write_niche(outroot, "warmtepomp", csv_rows=[], json_leads=[])

    result = subprocess.run(
        ["python3", str(SCRIPT), str(outroot)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert (outroot / "summary.md").exists()
    assert (outroot / "summary.json").exists()
