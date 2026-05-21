#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SUMMARY_RE = re.compile(
    r"\[(?P<niche>[^\]]+)\]\s+raw=(?P<raw>\d+)\s+->\s+leads=(?P<leads>\d+)\s+"
    r"\(promo=(?P<promo>\d+)\s+oud=(?P<oud>\d+)\s+low=(?P<low>\d+)\s+"
    r"no_ts=(?P<no_ts>\d+)\s+hardblock=(?P<hardblock>\d+)\s+fuzzy=(?P<fuzzy>\d+)"
)
INLINE_LLM_RE = re.compile(
    r"llm_calls(?:=|\s+total=)(?P<total>\d+)"
    r"(?:.*?\bapi(?:_calls)?=(?P<api>\d+))?"
    r"(?:.*?\bcache(?:_hits)?=(?P<cache>\d+)(?:/\d+)?)?"
    r"(?:.*?\bcost=(?:EUR|€)?(?P<cost>[0-9]+(?:\.[0-9]+)?))?",
    re.IGNORECASE,
)
HUMAN_LLM_RE = re.compile(
    r"LLM\s*:\s*(?P<api>\d+)\s+API calls\s+~(?:EUR|€)?(?P<cost>[0-9]+(?:\.[0-9]+)?)"
    r".*?cache_hits=(?P<cache>\d+)/(?P<total>\d+)",
    re.IGNORECASE,
)
SHEETS_SUMMARY_RE = re.compile(
    r"sheets\s+HOT\s+\+(?P<hot>\d+)\s+ALL\s+\+(?P<all>\d+)\s+OPP\s+\+(?P<opp>\d+)",
    re.IGNORECASE,
)
SHEETS_DETAIL_RE = re.compile(
    r"Sheets:\s+\+(?P<count>\d+)\s+leads\s+in\s+'(?P<tab>[^']+)'",
    re.IGNORECASE,
)


def _timestamp_from_outroot(outroot: Path) -> str:
    name = outroot.name
    prefix = "full_rehearsal_"
    if name.startswith(prefix):
        return name[len(prefix) :]
    return name


def _source_baseline() -> str:
    try:
        from consumer.sources import PROOF_SPRINT_SOURCES
    except Exception:
        return "unknown"
    return ",".join(PROOF_SPRINT_SOURCES)


def _read_exit_code(niche_dir: Path) -> tuple[int | None, str]:
    path = niche_dir / ".exit_code"
    if not path.exists():
        return None, "MISSING"

    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    try:
        return int(raw), raw
    except ValueError:
        return None, raw or "MISSING"


def _parse_run_log(path: Path) -> dict[str, Any]:
    counts: dict[str, int | None] = {
        "raw": None,
        "leads": None,
        "promo": None,
        "oud": None,
        "low": None,
        "no_ts": None,
        "hardblock": None,
        "fuzzy": None,
    }
    llm_calls = {"total": 0, "api": 0, "cache": 0, "cost_eur": 0.0}
    detailed_sheets = {"hot": 0, "all": 0, "opp": 0}
    summary_sheets: dict[str, int] | None = None
    error_count = 0
    llm_seen_inline = False

    if not path.exists():
        return {
            "counts": counts,
            "llm_calls": llm_calls,
            "sheets_writes": detailed_sheets,
            "error_count": error_count,
            "run_log_present": False,
        }

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "ERROR" in line or "Traceback" in line:
            error_count += 1

        summary = SUMMARY_RE.search(line)
        if summary:
            for key in counts:
                counts[key] = int(summary.group(key))

        inline_llm = INLINE_LLM_RE.search(line)
        if inline_llm:
            total = int(inline_llm.group("total"))
            api = int(inline_llm.group("api") or total)
            cache = int(inline_llm.group("cache") or 0)
            cost = float(inline_llm.group("cost") or 0.0)
            llm_calls = {
                "total": total,
                "api": api,
                "cache": cache,
                "cost_eur": cost,
            }
            llm_seen_inline = True

        human_llm = HUMAN_LLM_RE.search(line)
        if human_llm and not llm_seen_inline:
            llm_calls = {
                "total": int(human_llm.group("total")),
                "api": int(human_llm.group("api")),
                "cache": int(human_llm.group("cache")),
                "cost_eur": float(human_llm.group("cost")),
            }

        sheets_summary = SHEETS_SUMMARY_RE.search(line)
        if sheets_summary:
            summary_sheets = {
                "hot": int(sheets_summary.group("hot")),
                "all": int(sheets_summary.group("all")),
                "opp": int(sheets_summary.group("opp")),
            }

        sheets_detail = SHEETS_DETAIL_RE.search(line)
        if sheets_detail:
            count = int(sheets_detail.group("count"))
            tab = sheets_detail.group("tab").upper()
            if "HOT" in tab:
                detailed_sheets["hot"] += count
            elif "ALL" in tab:
                detailed_sheets["all"] += count
            elif "OPP" in tab:
                detailed_sheets["opp"] += count

    return {
        "counts": counts,
        "llm_calls": llm_calls,
        "sheets_writes": summary_sheets or detailed_sheets,
        "error_count": error_count,
        "run_log_present": True,
    }


def _count_csv_rows(paths: list[Path]) -> int:
    total = 0
    for path in paths:
        try:
            with path.open(newline="", encoding="utf-8", errors="replace") as handle:
                rows = list(csv.reader(handle))
        except OSError:
            continue
        if rows:
            total += max(len(rows) - 1, 0)
    return total


def _coerce_leads(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        leads = payload.get("leads")
        if isinstance(leads, list):
            return [item for item in leads if isinstance(item, dict)]
    return []


def _load_json_leads(paths: list[Path]) -> tuple[list[dict[str, Any]], bool]:
    leads: list[dict[str, Any]] = []
    malformed = False
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            malformed = True
            continue
        leads.extend(_coerce_leads(payload))
    return leads, malformed


def _score(lead: dict[str, Any]) -> float:
    try:
        return float(lead.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _display_score(score: float) -> int | float:
    if score.is_integer():
        return int(score)
    return round(score, 2)


def _compact_text(value: Any, limit: int = 140) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _lead_summary(lead: dict[str, Any], niche: str) -> dict[str, Any]:
    score = _score(lead)
    title = _compact_text(lead.get("title"))
    snippet = _compact_text(
        lead.get("summary") or lead.get("snippet") or lead.get("text") or title
    )
    return {
        "id": str(lead.get("id") or ""),
        "niche": str(lead.get("niche") or niche),
        "score": _display_score(score),
        "url": str(lead.get("url") or ""),
        "title": title,
        "snippet": snippet,
    }


def _summarize_niche(niche_dir: Path) -> dict[str, Any]:
    niche = niche_dir.name
    exit_code, exit_code_raw = _read_exit_code(niche_dir)
    log = _parse_run_log(niche_dir / "run.log")
    csv_paths = sorted(niche_dir.glob("leads_*.csv"))
    json_paths = sorted(niche_dir.glob("leads_*.json"))
    csv_rows = _count_csv_rows(csv_paths)
    json_leads, json_malformed = _load_json_leads(json_paths)
    sorted_leads = sorted(json_leads, key=_score, reverse=True)
    top_leads = [_lead_summary(lead, niche) for lead in sorted_leads[:3]]
    receipt_candidates = [
        _lead_summary(lead, niche) for lead in sorted_leads if _score(lead) >= 70
    ]

    if exit_code == 0 and csv_rows >= 1:
        status = "PASS"
    elif exit_code == 0:
        status = "WARN"
    else:
        status = "FAIL"

    return {
        "niche": niche,
        "status": status,
        "exit_code": exit_code,
        "exit_code_raw": exit_code_raw,
        "run_log": str(niche_dir / "run.log") if (niche_dir / "run.log").exists() else None,
        "run_log_present": log["run_log_present"],
        "counts": log["counts"],
        "llm_calls": log["llm_calls"],
        "sheets_writes": log["sheets_writes"],
        "error_count": log["error_count"],
        "csv_files": [str(path) for path in csv_paths],
        "csv_row_count": csv_rows,
        "json_files": [str(path) for path in json_paths],
        "json_lead_count": len(json_leads),
        "json_malformed": json_malformed,
        "top_leads": top_leads,
        "receipt_candidates": receipt_candidates,
    }


def _aggregate(niches: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    sheets = {"hot": 0, "all": 0, "opp": 0, "total": 0}
    total_llm_calls = 0
    total_llm_api = 0
    total_llm_cache = 0
    total_llm_cost = 0.0

    for niche in niches:
        status_counts[niche["status"]] += 1
        total_llm_calls += int(niche["llm_calls"].get("total") or 0)
        total_llm_api += int(niche["llm_calls"].get("api") or 0)
        total_llm_cache += int(niche["llm_calls"].get("cache") or 0)
        total_llm_cost += float(niche["llm_calls"].get("cost_eur") or 0.0)
        for key in ("hot", "all", "opp"):
            sheets[key] += int(niche["sheets_writes"].get(key) or 0)

    sheets["total"] = sheets["hot"] + sheets["all"] + sheets["opp"]
    return {
        "total_leads": sum(int(niche["csv_row_count"]) for niche in niches),
        "llm_calls": {
            "total": total_llm_calls,
            "api": total_llm_api,
            "cache": total_llm_cache,
            "cost_eur": round(total_llm_cost, 6),
        },
        "sheets_writes": sheets,
        "status_counts": status_counts,
    }


def _md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _count_or_blank(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Full-System Rehearsal {summary['timestamp']}",
        "",
        f"Source baseline: PROOF_SPRINT_SOURCES={summary['env']['PROOF_SPRINT_SOURCES']}",
        "",
        "Env settings:",
        "- LEAD_RADAR_SHEETS_OPP_FLOOR=40",
        "- LEAD_RADAR_LLM_BUDGET_EUR=3.00 per niche",
        "",
        "## Per-Niche Results",
        "",
        "| Niche | Status | Exit | CSV Leads | Raw | Log Leads | HOT+ | ALL+ | OPP+ | LLM Calls | LLM EUR | Errors |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for niche in summary["niches"]:
        lines.append(
            "| {niche} | {status} | {exit_code} | {csv_leads} | {raw} | {log_leads} | "
            "{hot} | {all_} | {opp} | {llm_calls} | {llm_cost:.4f} | {errors} |".format(
                niche=_md_escape(niche["niche"]),
                status=niche["status"],
                exit_code=_md_escape(niche["exit_code_raw"]),
                csv_leads=niche["csv_row_count"],
                raw=_count_or_blank(niche["counts"].get("raw")),
                log_leads=_count_or_blank(niche["counts"].get("leads")),
                hot=niche["sheets_writes"].get("hot", 0),
                all_=niche["sheets_writes"].get("all", 0),
                opp=niche["sheets_writes"].get("opp", 0),
                llm_calls=niche["llm_calls"].get("total", 0),
                llm_cost=float(niche["llm_calls"].get("cost_eur") or 0.0),
                errors=niche["error_count"],
            )
        )

    lines.extend(["", "## Top Leads Per Niche", ""])
    for niche in summary["niches"]:
        lines.append(f"### {_md_escape(niche['niche'])}")
        if not niche["top_leads"]:
            lines.append("- No JSON leads found.")
            lines.append("")
            continue
        for lead in niche["top_leads"]:
            label = lead["title"] or lead["snippet"] or "(untitled)"
            lines.append(
                f"- [{lead['score']}] {_md_escape(lead['id'])} "
                f"{_md_escape(label)} - {_md_escape(lead['url'])}"
            )
        lines.append("")

    receipt_candidates = [
        lead for niche in summary["niches"] for lead in niche["receipt_candidates"]
    ]
    receipt_candidates = sorted(receipt_candidates, key=lambda lead: float(lead["score"]), reverse=True)
    lines.extend(
        [
            "## Receipt Candidates",
            "",
            "Receipt export requires approved JSONL + lead_id via run_export_receipt.py.",
            "",
        ]
    )
    if receipt_candidates:
        lines.extend(
            [
                "| Lead ID | Niche | Score | URL | Title/Snippet |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for lead in receipt_candidates:
            label = lead["title"] or lead["snippet"]
            lines.append(
                f"| {_md_escape(lead['id'])} | {_md_escape(lead['niche'])} | {lead['score']} | "
                f"{_md_escape(lead['url'])} | {_md_escape(label)} |"
            )
    else:
        lines.append("No receipt candidates with score >= 70.")

    aggregate = summary["aggregate"]
    lines.extend(
        [
            "",
            "## Aggregate Totals",
            "",
            f"- Total leads: {aggregate['total_leads']}",
            f"- Total LLM calls: {aggregate['llm_calls']['total']}",
            f"- Total estimated LLM cost: EUR {aggregate['llm_calls']['cost_eur']:.4f}",
            f"- Total Sheets writes: {aggregate['sheets_writes']['total']} "
            f"(HOT {aggregate['sheets_writes']['hot']}, ALL {aggregate['sheets_writes']['all']}, "
            f"OPP {aggregate['sheets_writes']['opp']})",
            f"- PASS/WARN/FAIL: {aggregate['status_counts']['PASS']}/"
            f"{aggregate['status_counts']['WARN']}/{aggregate['status_counts']['FAIL']}",
            "",
        ]
    )
    return "\n".join(lines)


def summarize_outroot(outroot: Path) -> dict[str, Any]:
    outroot = outroot.resolve()
    niche_dirs = sorted(path for path in outroot.iterdir() if path.is_dir())
    summary = {
        "timestamp": _timestamp_from_outroot(outroot),
        "outroot": str(outroot),
        "env": {
            "LEAD_RADAR_SHEETS_OPP_FLOOR": os.environ.get(
                "LEAD_RADAR_SHEETS_OPP_FLOOR", "40"
            ),
            "LEAD_RADAR_LLM_BUDGET_EUR": os.environ.get(
                "LEAD_RADAR_LLM_BUDGET_EUR", "3.00"
            ),
            "PROOF_SPRINT_SOURCES": _source_baseline(),
        },
        "niches": [_summarize_niche(path) for path in niche_dirs],
        "aggregate": {},
    }
    summary["aggregate"] = _aggregate(summary["niches"])

    (outroot / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (outroot / "summary.md").write_text(_render_markdown(summary), encoding="utf-8")
    return summary


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python3 scripts/summarize_rehearsal_results.py <outroot>", file=sys.stderr)
        return 2

    outroot = Path(argv[1])
    if not outroot.exists() or not outroot.is_dir():
        print(f"ERROR: outroot is not a directory: {outroot}", file=sys.stderr)
        return 1

    summarize_outroot(outroot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
