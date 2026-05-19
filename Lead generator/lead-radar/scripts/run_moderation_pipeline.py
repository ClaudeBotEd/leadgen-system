#!/usr/bin/env python3
"""Run the moderation pipeline on a captured-posts JSONL/CSV.

Loads a file of public-post candidates (one per row), pushes every row
through /api/council/moderate-lead, persists APPROVED records, and emits:

  data/runs/<RUN_ID>/run_results.jsonl     — one ModerationResult per row
  data/runs/<RUN_ID>/run_summary.json      — machine-readable aggregate
  data/runs/<RUN_ID>/report.md             — human-readable report
  data/runs/<RUN_ID>/approved_leads.jsonl  — approved store (HOT-only, gated)

Input file is expected to contain one candidate per line/row with at
least: source_url, snippet, captured_at. Other fields (source_platform,
posted_at, region, niche, author_handle, candidate_id) are forwarded if
present. The doctrine input is a forum/social scrape, not a company CSV.

Usage:
  python scripts/run_moderation_pipeline.py --input data/captured_posts.jsonl
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from moderation import (  # noqa: E402
    CouncilClient,
    ModerationConfig,
    get_config,
    moderate_posts,
)


def load_candidates(path: Path, max_rows: Optional[int]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if path.suffix.lower() == ".jsonl":
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if max_rows and len(rows) >= max_rows:
                    break
    elif path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            rows = data
        if max_rows:
            rows = rows[:max_rows]
    else:
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(
                    {k: (v.strip() if isinstance(v, str) else v) for k, v in r.items() if v not in (None, "")}
                )
                if max_rows and len(rows) >= max_rows:
                    break
    return [
        r for r in rows
        if str(r.get("source_url") or "").strip()
        and str(r.get("snippet") or "").strip()
        and str(r.get("captured_at") or "").strip()
    ]


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def build_summary(
    candidates: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    wall_clock_seconds: float,
    config: ModerationConfig,
) -> Dict[str, Any]:
    reviewed = [r for r in results if r.get("review")]
    approved = [r for r in results if r.get("approved")]
    persisted = [r for r in results if r.get("persisted")]
    elapsed = [r.get("elapsed_ms") or 0 for r in results]

    def _usage_sum(r: Dict[str, Any], key: str) -> int:
        usage = r.get("usage") or {}
        try:
            return int(usage.get(key) or 0)
        except (TypeError, ValueError):
            return 0

    total_prompt = sum(_usage_sum(r, "prompt_tokens") for r in results)
    total_completion = sum(_usage_sum(r, "completion_tokens") for r in results)
    total_tokens = sum(_usage_sum(r, "total_tokens") for r in results)

    temperature_counts: Dict[str, int] = {}
    provenance_counts: Dict[str, int] = {}
    signal_counts: Dict[str, int] = {}
    error_kinds: Dict[str, int] = {}
    for r in reviewed:
        review = r["review"]
        t = (review.get("lead_temperature") or "UNKNOWN").upper()
        temperature_counts[t] = temperature_counts.get(t, 0) + 1
        p = (review.get("provenance_status") or "unknown").lower()
        provenance_counts[p] = provenance_counts.get(p, 0) + 1
        s = (review.get("signal_type") or "NONE").upper()
        signal_counts[s] = signal_counts.get(s, 0) + 1
    for r in results:
        if r.get("error_kind"):
            error_kinds[r["error_kind"]] = error_kinds.get(r["error_kind"], 0) + 1

    return {
        "totals": {
            "candidates_in": len(candidates),
            "reviewed": len(reviewed),
            "approved": len(approved),
            "persisted": len(persisted),
            "errors": sum(1 for r in results if r.get("error_kind")),
            "approval_rate_pct": round(100.0 * len(approved) / max(len(reviewed), 1), 1),
        },
        "latency_ms": {
            "moderate": {
                "p50": int(_percentile(elapsed, 50)),
                "p95": int(_percentile(elapsed, 95)),
                "max": max(elapsed) if elapsed else 0,
            },
            "wall_clock_seconds": round(wall_clock_seconds, 2),
            "throughput_candidates_per_min": round(60.0 * len(results) / max(wall_clock_seconds, 0.001), 2),
        },
        "tokens": {
            "prompt": total_prompt,
            "completion": total_completion,
            "total": total_tokens,
            "per_candidate_avg": int(total_tokens / max(len(results), 1)),
        },
        "temperature_counts": temperature_counts,
        "provenance_counts": provenance_counts,
        "signal_counts": signal_counts,
        "error_kinds": error_kinds,
        "config": {
            "strategy": config.strategy,
            "approved_temperatures": list(config.approved_temperatures),
            "min_confidence_band": config.min_confidence_band,
            "require_provenance": list(config.require_provenance),
            "max_concurrent": config.max_concurrent,
            "council_url": config.council_url,
        },
    }


def _format_lead_block(candidate: Dict[str, Any], review: Dict[str, Any], approval: Dict[str, Any]) -> str:
    snippet = (review.get("verbatim_snippet") or candidate.get("snippet") or "").strip()
    lines: List[str] = []
    lines.append("```")
    lines.append(f"candidate_id         : {candidate.get('candidate_id', '-')}")
    lines.append(f"source_url           : {candidate.get('source_url', '-')}")
    lines.append(f"source_platform      : {candidate.get('source_platform', '-')}")
    lines.append(f"captured_at          : {review.get('captured_at') or candidate.get('captured_at', '-')}")
    lines.append(f"lead_temperature     : {review.get('lead_temperature')}")
    lines.append(f"confidence_band      : {review.get('confidence_band')}")
    lines.append(f"provenance_status    : {review.get('provenance_status')}")
    lines.append(f"signal_type          : {review.get('signal_type')}")
    lines.append(f"purchase_window      : {review.get('estimated_purchase_window')}")
    lines.append(f"value_band           : {review.get('estimated_install_value_band')}")
    lines.append(f"source_quality       : {review.get('source_quality')}")
    lines.append(f"duplicate_risk       : {review.get('duplicate_risk')}")
    lines.append(f"review_required      : {review.get('review_required')}")
    lines.append(f"approval             : {approval.get('approved')} — {approval.get('reason')}")
    lines.append("```")
    lines.append("")
    if snippet:
        lines.append("**Verbatim snippet (never paraphrased):**")
        lines.append("")
        lines.append("> " + snippet.replace("\n", "\n> "))
        lines.append("")
    if review.get("intent_summary"):
        lines.append(f"**Intent summary:** {review['intent_summary']}")
        lines.append("")
    if review.get("homeowner_motivation"):
        lines.append(f"**Homeowner motivation:** {review['homeowner_motivation']}")
        lines.append("")
    flags = review.get("trust_flags") or []
    if flags:
        lines.append("**Trust flags:**")
        for f in flags:
            lines.append(f"- {f}")
        lines.append("")
    if review.get("rejection_reason"):
        lines.append(f"**Rejection reason:** {review['rejection_reason']}")
        lines.append("")
    if review.get("reviewer_notes"):
        lines.append(f"**Reviewer notes:** {review['reviewer_notes']}")
        lines.append("")
    return "\n".join(lines)


def render_markdown(
    summary: Dict[str, Any],
    sorted_results: List[Dict[str, Any]],
    candidates_by_id: Dict[str, Dict[str, Any]],
    run_id: str,
    started_at: str,
) -> str:
    t = summary["totals"]
    lat = summary["latency_ms"]
    tok = summary["tokens"]
    cfg = summary["config"]

    lines: List[str] = []
    lines.append(f"# Moderation Pipeline Run — `{run_id}`")
    lines.append("")
    lines.append(f"Started: `{started_at}`")
    lines.append("")
    lines.append("Doctrine: provenance > volume. HOT-only delivery. One lead, one installer.")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"- Candidates in: **{t['candidates_in']}**")
    lines.append(f"- Reviewed by council: **{t['reviewed']}**")
    lines.append(f"- Approved (cleared HOT gate): **{t['approved']}**")
    lines.append(f"- Persisted to approved_leads.jsonl: **{t['persisted']}**")
    lines.append(f"- Approval rate: **{t['approval_rate_pct']}%**")
    lines.append(f"- Errors: **{t['errors']}**")
    lines.append("")
    lines.append("## Approval gate in effect")
    lines.append("")
    lines.append(f"- approved_temperatures: `{cfg['approved_temperatures']}`")
    lines.append(f"- min_confidence_band: `{cfg['min_confidence_band']}`")
    lines.append(f"- require_provenance: `{cfg['require_provenance']}`")
    lines.append("")
    lines.append("## Latency & throughput")
    lines.append("")
    lines.append("| Stage | p50 (ms) | p95 (ms) | max (ms) |")
    lines.append("| --- | --- | --- | --- |")
    lines.append(
        f"| moderate-lead | {lat['moderate']['p50']} | {lat['moderate']['p95']} | {lat['moderate']['max']} |"
    )
    lines.append("")
    lines.append(f"- Wall-clock: **{lat['wall_clock_seconds']} s**")
    lines.append(
        f"- Throughput: **{lat['throughput_candidates_per_min']} candidates/min** "
        f"(max_concurrent={cfg['max_concurrent']})"
    )
    lines.append("")
    lines.append("## Token usage")
    lines.append("")
    lines.append(f"- Prompt tokens: **{tok['prompt']:,}**")
    lines.append(f"- Completion tokens: **{tok['completion']:,}**")
    lines.append(f"- Total tokens: **{tok['total']:,}**")
    lines.append(f"- Per-candidate avg: **{tok['per_candidate_avg']:,}**")
    if tok["total"]:
        est_cost = (tok["prompt"] * 2.0 + tok["completion"] * 8.0) / 1_000_000
        lines.append(f"- Estimated cost (gpt-4.1 list prices): **${est_cost:.4f}**")
    lines.append("")
    lines.append("## Temperature distribution")
    lines.append("")
    for k, v in sorted(summary["temperature_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Provenance status distribution")
    lines.append("")
    for k, v in sorted(summary["provenance_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Signal-type distribution")
    lines.append("")
    for k, v in sorted(summary["signal_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"- {k}: {v}")
    lines.append("")
    if summary["error_kinds"]:
        lines.append("## Error breakdown")
        lines.append("")
        for k, v in summary["error_kinds"].items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")

    def _pick(temp: str) -> Optional[Dict[str, Any]]:
        for r in sorted_results:
            if (r.get("review") or {}).get("lead_temperature") == temp:
                return r
        return None

    for label, temp in (
        ("Approved HOT example", "HOT"),
        ("WARM example", "WARM"),
        ("OPP / rejected example", "OPP"),
    ):
        chosen = _pick(temp)
        if chosen is None:
            continue
        lines.append("---")
        lines.append("")
        lines.append(f"## {label}")
        lines.append("")
        candidate = candidates_by_id.get(chosen.get("candidate_id") or "", {})
        lines.append(_format_lead_block(candidate, chosen["review"], chosen.get("approval") or {}))

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path,
                        help="Path to captured posts (.jsonl, .json array, or .csv)")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--strategy", choices=["fast", "council"], default=None)
    parser.add_argument("--max-concurrent", type=int, default=None)
    parser.add_argument("--council-url", default=None)
    args = parser.parse_args()

    config = get_config()
    if args.strategy is not None:
        config = dataclasses.replace(config, strategy=args.strategy)
    if args.max_concurrent is not None:
        config = dataclasses.replace(config, max_concurrent=args.max_concurrent)
    if args.council_url is not None:
        config = dataclasses.replace(config, council_url=args.council_url)
    if not config.enabled:
        config = dataclasses.replace(config, enabled=True)

    input_path: Path = args.input
    if not input_path.is_absolute():
        input_path = HERE / input_path
    candidates = load_candidates(input_path, args.max_rows)
    if not candidates:
        print(
            f"ERROR: no post-shaped rows in {input_path} "
            "(each row needs source_url + snippet + captured_at)",
            file=sys.stderr,
        )
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = HERE / "data" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    config = dataclasses.replace(config, approved_path=run_dir / "approved_leads.jsonl")

    print(f"[run] id={run_id}")
    print(f"[run] candidates={len(candidates)} strategy={config.strategy} "
          f"concurrent={config.max_concurrent}")
    print(f"[run] council_url={config.council_url}")
    print(f"[run] approval gate: temp={config.approved_temperatures} "
          f"confidence>={config.min_confidence_band} "
          f"provenance={config.require_provenance}")
    print(f"[run] output_dir={run_dir}")

    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    t0 = time.monotonic()
    with CouncilClient(config) as client:
        try:
            health = client.health()
            print(f"[run] council health: {health.get('status')}")
        except Exception as e:
            print(f"ERROR: council unreachable: {e}", file=sys.stderr)
            return 2
        summary_obj = moderate_posts(candidates, config=config, client=client)
    wall_clock = time.monotonic() - t0

    results = [dataclasses.asdict(r) for r in summary_obj.results]

    with (run_dir / "run_results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

    candidates_by_id = {c.get("candidate_id") or "": c for c in candidates}
    sorted_results = sorted(
        [r for r in results if r.get("review")],
        key=lambda r: (
            {"HOT": 0, "WARM": 1, "OPP": 2}.get(
                (r.get("review") or {}).get("lead_temperature") or "OPP", 3
            ),
            -1 if (r.get("review") or {}).get("provenance_status") == "verified" else 0,
        ),
    )
    aggregate = build_summary(candidates, results, wall_clock, config)
    (run_dir / "run_summary.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    report_md = render_markdown(aggregate, sorted_results, candidates_by_id, run_id, started_at)
    (run_dir / "report.md").write_text(report_md, encoding="utf-8")

    print()
    print(f"[run] wall_clock={wall_clock:.1f}s")
    print(
        f"[run] reviewed={summary_obj.reviewed} approved={summary_obj.approved} "
        f"persisted={summary_obj.persisted} webhooks={summary_obj.webhooks_fired} "
        f"errors={summary_obj.errors}"
    )
    print(f"[run] tokens total={aggregate['tokens']['total']:,}")
    print(f"[run] report: {run_dir / 'report.md'}")
    print(f"[run] approved store: {config.approved_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
