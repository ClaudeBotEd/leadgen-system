#!/usr/bin/env python3
"""Run the full AI intelligence pipeline on a real lead CSV.

Loads a scraped leads CSV (default: data/leads_master.csv), pushes every
row through the llm-council intelligence layer, persists qualified leads
to the CRM JSONL store, and emits three artefacts:

  data/runs/<RUN_ID>/run_results.jsonl   — one EnrichmentResult per lead
  data/runs/<RUN_ID>/run_summary.json    — machine-readable aggregate
  data/runs/<RUN_ID>/report.md           — human-readable report
  data/runs/<RUN_ID>/qualified_leads.jsonl — CRM JSONL for this run

Usage:
  python scripts/run_intelligence_pipeline.py \
      --input data/leads_master.csv \
      --max-leads 27 \
      --threshold 6 \
      --strategy fast
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from intelligence import (  # noqa: E402
    CouncilClient,
    IntelligenceConfig,
    enrich_leads,
    get_config,
)


def load_leads(path: Path, max_leads: Optional[int]) -> List[Dict[str, Any]]:
    leads: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            row = {k: v for k, v in row.items() if v not in (None, "")}
            leads.append(row)
            if max_leads and len(leads) >= max_leads:
                break
    return leads


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


def _format_lead_block(
    lead: Dict[str, Any],
    intel: Dict[str, Any],
    seq: Optional[Dict[str, Any]],
) -> str:
    company = intel.get("company_name") or lead.get("company_name") or "(unknown)"
    lines: List[str] = []
    lines.append(f"### {company}")
    lines.append("")
    lines.append("```")
    lines.append(f"lead_id              : {lead.get('lead_id', '-')}")
    lines.append(f"domain               : {lead.get('domain', '-')}")
    lines.append(f"intent_score (scrape): {lead.get('intent_score', '-')}")
    lines.append(f"lead_quality_score   : {intel.get('lead_quality_score')}/10")
    lines.append(f"automation_fit_score : {intel.get('automation_fit_score')}/10")
    lines.append(f"urgency_score        : {intel.get('urgency_score')}/10")
    lines.append(f"outbound_potential   : {intel.get('outbound_potential')}/10")
    lines.append(f"confidence_score     : {intel.get('confidence_score')}/10")
    lines.append(f"estimated_budget     : {intel.get('estimated_budget')}")
    lines.append(f"recommended_channel  : {intel.get('recommended_channel')}")
    lines.append("```")
    lines.append("")
    lines.append(f"**Recommended offer:** {intel.get('recommended_offer')}")
    lines.append("")
    lines.append(f"**Best outreach angle:** {intel.get('best_outreach_angle')}")
    lines.append("")
    opps = intel.get("ai_opportunities") or []
    if opps:
        lines.append("**AI opportunities:**")
        for o in opps:
            lines.append(f"- {o}")
        lines.append("")
    pains = intel.get("pain_points") or []
    if pains:
        lines.append("**Pain points:**")
        for p in pains:
            lines.append(f"- {p}")
        lines.append("")
    rationale = intel.get("rationale")
    if rationale:
        lines.append(f"**Council reasoning:** {rationale}")
        lines.append("")
    if seq:
        cold = seq.get("cold_email") or {}
        if cold.get("subject") or cold.get("body"):
            lines.append("**Cold email draft:**")
            lines.append("")
            lines.append("> **Subject:** " + (cold.get("subject") or ""))
            lines.append(">")
            for body_line in (cold.get("body") or "").split("\n"):
                lines.append(f"> {body_line}" if body_line else ">")
            lines.append("")
        linkedin = seq.get("linkedin_opener")
        if linkedin:
            lines.append(f"**LinkedIn opener:** {linkedin}")
            lines.append("")
        followups = seq.get("follow_up_sequence") or []
        if followups:
            lines.append("**Follow-up sequence:**")
            for step in followups:
                day = step.get("day")
                channel = step.get("channel")
                subj = step.get("subject") or ""
                body = (step.get("body") or "").replace("\n", " ").strip()
                head = f"- Day {day} ({channel})"
                if subj:
                    head += f" — *{subj}*"
                lines.append(head)
                if body:
                    truncated = body[:240] + ("…" if len(body) > 240 else "")
                    lines.append(f"  > {truncated}")
            lines.append("")
        ctas = seq.get("cta_suggestions") or []
        if ctas:
            lines.append("**CTA suggestions:**")
            for c in ctas:
                lines.append(f"- {c}")
            lines.append("")
    return "\n".join(lines)


def build_summary(
    leads: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    wall_clock_seconds: float,
    config: IntelligenceConfig,
) -> Dict[str, Any]:
    scored = [r for r in results if r.get("intelligence")]
    qualified = [r for r in results if r.get("saved")]

    def _intel_int(r: Dict[str, Any], key: str) -> int:
        try:
            return int((r.get("intelligence") or {}).get(key) or 0)
        except (TypeError, ValueError):
            return 0

    quality_scores = [_intel_int(r, "lead_quality_score") for r in scored]
    automation_scores = [_intel_int(r, "automation_fit_score") for r in scored]
    urgency_scores = [_intel_int(r, "urgency_score") for r in scored]
    confidence_scores = [_intel_int(r, "confidence_score") for r in scored]
    score_elapsed = [r.get("elapsed_ms_score") or 0 for r in results]
    seq_elapsed = [r.get("elapsed_ms_sequence") or 0 for r in results if r.get("elapsed_ms_sequence")]

    def _usage_sum(r: Dict[str, Any], key: str) -> int:
        total = 0
        for usage_key in ("score_usage", "sequence_usage"):
            usage = r.get(usage_key) or {}
            try:
                total += int(usage.get(key) or 0)
            except (TypeError, ValueError):
                pass
        return total

    total_prompt = sum(_usage_sum(r, "prompt_tokens") for r in results)
    total_completion = sum(_usage_sum(r, "completion_tokens") for r in results)
    total_tokens = sum(_usage_sum(r, "total_tokens") for r in results)

    error_kinds: Dict[str, int] = {}
    for r in results:
        if r.get("error_kind"):
            error_kinds[r["error_kind"]] = error_kinds.get(r["error_kind"], 0) + 1

    distribution = {str(i): 0 for i in range(11)}
    for s in quality_scores:
        distribution[str(s)] = distribution.get(str(s), 0) + 1

    channel_counts: Dict[str, int] = {}
    for r in scored:
        channel = (r.get("intelligence") or {}).get("recommended_channel") or "unknown"
        channel_counts[channel] = channel_counts.get(channel, 0) + 1

    return {
        "totals": {
            "leads_input": len(leads),
            "scored": len(scored),
            "qualified": len(qualified),
            "errors": sum(1 for r in results if r.get("error_kind")),
            "qualification_rate_pct": round(100.0 * len(qualified) / max(len(scored), 1), 1),
        },
        "latency_ms": {
            "score": {
                "p50": int(_percentile(score_elapsed, 50)),
                "p95": int(_percentile(score_elapsed, 95)),
                "max": max(score_elapsed) if score_elapsed else 0,
            },
            "sequence": {
                "p50": int(_percentile(seq_elapsed, 50)) if seq_elapsed else 0,
                "p95": int(_percentile(seq_elapsed, 95)) if seq_elapsed else 0,
                "max": max(seq_elapsed) if seq_elapsed else 0,
            },
            "wall_clock_seconds": round(wall_clock_seconds, 2),
            "throughput_leads_per_min": round(60.0 * len(results) / max(wall_clock_seconds, 0.001), 2),
        },
        "tokens": {
            "prompt": total_prompt,
            "completion": total_completion,
            "total": total_tokens,
            "per_lead_avg": int(total_tokens / max(len(results), 1)),
        },
        "score_distribution": distribution,
        "quality_score_stats": {
            "mean": round(statistics.mean(quality_scores), 2) if quality_scores else 0,
            "median": statistics.median(quality_scores) if quality_scores else 0,
            "min": min(quality_scores) if quality_scores else 0,
            "max": max(quality_scores) if quality_scores else 0,
        },
        "automation_fit_stats": {
            "mean": round(statistics.mean(automation_scores), 2) if automation_scores else 0,
            "median": statistics.median(automation_scores) if automation_scores else 0,
        },
        "urgency_stats": {
            "mean": round(statistics.mean(urgency_scores), 2) if urgency_scores else 0,
        },
        "confidence_stats": {
            "mean": round(statistics.mean(confidence_scores), 2) if confidence_scores else 0,
            "median": statistics.median(confidence_scores) if confidence_scores else 0,
        },
        "channel_recommendations": channel_counts,
        "error_kinds": error_kinds,
        "config": {
            "strategy": config.score_strategy,
            "quality_threshold": config.quality_threshold,
            "max_concurrent": config.max_concurrent,
            "council_url": config.council_url,
            "generate_sequence": config.generate_sequence,
        },
    }


def render_markdown(
    summary: Dict[str, Any],
    sorted_results: List[Dict[str, Any]],
    leads_by_id: Dict[str, Dict[str, Any]],
    run_id: str,
    started_at: str,
) -> str:
    t = summary["totals"]
    lat = summary["latency_ms"]
    tok = summary["tokens"]
    cfg = summary["config"]

    lines: List[str] = []
    lines.append(f"# Lead Intelligence Pipeline Run — `{run_id}`")
    lines.append("")
    lines.append(f"Started: `{started_at}`")
    lines.append("")
    lines.append("## Totals")
    lines.append("")
    lines.append(f"- Leads in: **{t['leads_input']}**")
    lines.append(f"- Successfully scored: **{t['scored']}**")
    lines.append(f"- Qualified (≥ threshold {cfg['quality_threshold']}): **{t['qualified']}**")
    lines.append(f"- Qualification rate: **{t['qualification_rate_pct']}%**")
    lines.append(f"- Errors: **{t['errors']}**")
    lines.append("")
    lines.append("## Latency & throughput")
    lines.append("")
    lines.append("| Stage | p50 (ms) | p95 (ms) | max (ms) |")
    lines.append("| --- | --- | --- | --- |")
    lines.append(
        f"| score-lead | {lat['score']['p50']} | {lat['score']['p95']} | {lat['score']['max']} |"
    )
    lines.append(
        f"| generate-sequence | {lat['sequence']['p50']} | {lat['sequence']['p95']} | {lat['sequence']['max']} |"
    )
    lines.append("")
    lines.append(f"- Wall-clock: **{lat['wall_clock_seconds']} s**")
    lines.append(f"- Throughput: **{lat['throughput_leads_per_min']} leads/min** (max_concurrent={cfg['max_concurrent']})")
    lines.append("")
    lines.append("## Token usage")
    lines.append("")
    lines.append(f"- Prompt tokens: **{tok['prompt']:,}**")
    lines.append(f"- Completion tokens: **{tok['completion']:,}**")
    lines.append(f"- Total tokens: **{tok['total']:,}**")
    lines.append(f"- Per-lead avg: **{tok['per_lead_avg']:,}**")
    if tok["total"]:
        # gpt-4.1 list prices (approximate): $2.00 / 1M input, $8.00 / 1M output.
        est_cost = (tok["prompt"] * 2.0 + tok["completion"] * 8.0) / 1_000_000
        lines.append(f"- Estimated cost (gpt-4.1 list prices): **${est_cost:.4f}**")
    lines.append("")
    lines.append("## Score distribution (lead_quality_score)")
    lines.append("")
    lines.append("| Score | Count | Bar |")
    lines.append("| --- | --- | --- |")
    dist = summary["score_distribution"]
    max_bar = max(dist.values()) if dist.values() else 0
    for i in range(11):
        n = dist.get(str(i), 0)
        bar = "█" * (n if max_bar <= 30 else int(30 * n / max_bar))
        lines.append(f"| {i} | {n} | {bar} |")
    lines.append("")
    lines.append("## Aggregate stats")
    lines.append("")
    qs = summary["quality_score_stats"]
    auto = summary["automation_fit_stats"]
    urg = summary["urgency_stats"]
    conf = summary["confidence_stats"]
    lines.append(
        f"- Lead quality score — mean {qs['mean']} / median {qs['median']} / min {qs['min']} / max {qs['max']}"
    )
    lines.append(f"- Automation fit — mean {auto['mean']} / median {auto['median']}")
    lines.append(f"- Urgency — mean {urg['mean']}")
    lines.append(f"- Confidence — mean {conf['mean']} / median {conf['median']}")
    lines.append("")
    lines.append("## Channel mix (council recommendation)")
    lines.append("")
    for k, v in sorted(summary["channel_recommendations"].items(), key=lambda x: -x[1]):
        lines.append(f"- {k}: {v}")
    lines.append("")

    if summary["error_kinds"]:
        lines.append("## Error breakdown")
        lines.append("")
        for k, v in summary["error_kinds"].items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")

    if sorted_results:
        best = sorted_results[0]
        worst = sorted_results[-1]
        median = sorted_results[len(sorted_results) // 2]
        lines.append("---")
        lines.append("")
        lines.append("## Best lead")
        lines.append("")
        lines.append(_format_lead_block(
            leads_by_id.get(best.get("lead_id") or "", {}),
            best.get("intelligence") or {},
            best.get("sequence"),
        ))
        lines.append("---")
        lines.append("")
        lines.append("## Median lead")
        lines.append("")
        lines.append(_format_lead_block(
            leads_by_id.get(median.get("lead_id") or "", {}),
            median.get("intelligence") or {},
            median.get("sequence"),
        ))
        lines.append("---")
        lines.append("")
        lines.append("## Worst lead")
        lines.append("")
        lines.append(_format_lead_block(
            leads_by_id.get(worst.get("lead_id") or "", {}),
            worst.get("intelligence") or {},
            worst.get("sequence"),
        ))

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/leads_master.csv", type=Path)
    parser.add_argument("--max-leads", type=int, default=None)
    parser.add_argument("--threshold", type=int, default=None,
                        help="Override LEAD_RADAR_INTELLIGENCE_QUALITY_THRESHOLD")
    parser.add_argument("--strategy", choices=["fast", "council"], default=None)
    parser.add_argument("--max-concurrent", type=int, default=None)
    parser.add_argument("--council-url", default=None)
    args = parser.parse_args()

    config = get_config()
    if args.threshold is not None:
        config = dataclasses.replace(config, quality_threshold=args.threshold)
    if args.strategy is not None:
        config = dataclasses.replace(config, score_strategy=args.strategy)
    if args.max_concurrent is not None:
        config = dataclasses.replace(config, max_concurrent=args.max_concurrent)
    if args.council_url is not None:
        config = dataclasses.replace(config, council_url=args.council_url)
    if not config.enabled:
        config = dataclasses.replace(config, enabled=True)

    leads_path: Path = args.input
    if not leads_path.is_absolute():
        leads_path = HERE / leads_path
    leads = load_leads(leads_path, args.max_leads)
    if not leads:
        print(f"ERROR: no leads found in {leads_path}", file=sys.stderr)
        return 1

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = HERE / "data" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    config = dataclasses.replace(config, crm_path=run_dir / "qualified_leads.jsonl")

    print(f"[run] id={run_id}")
    print(f"[run] leads={len(leads)} threshold={config.quality_threshold} "
          f"strategy={config.score_strategy} concurrent={config.max_concurrent}")
    print(f"[run] council_url={config.council_url}")
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
        summary_obj = enrich_leads(leads, config=config, client=client)
    wall_clock = time.monotonic() - t0

    results = [dataclasses.asdict(r) for r in summary_obj.results]

    with (run_dir / "run_results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

    leads_by_id = {l.get("lead_id", ""): l for l in leads}
    sorted_results = sorted(
        [r for r in results if r.get("intelligence")],
        key=lambda r: int((r.get("intelligence") or {}).get("lead_quality_score") or 0),
        reverse=True,
    )
    aggregate = build_summary(leads, results, wall_clock, config)
    (run_dir / "run_summary.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    report_md = render_markdown(aggregate, sorted_results, leads_by_id, run_id, started_at)
    (run_dir / "report.md").write_text(report_md, encoding="utf-8")

    print()
    print(f"[run] wall_clock={wall_clock:.1f}s")
    print(f"[run] scored={summary_obj.scored} qualified={summary_obj.qualified} "
          f"persisted={summary_obj.persisted} webhooks={summary_obj.webhooks_fired} "
          f"errors={summary_obj.errors}")
    print(f"[run] tokens total={aggregate['tokens']['total']:,} "
          f"prompt={aggregate['tokens']['prompt']:,} "
          f"completion={aggregate['tokens']['completion']:,}")
    print(f"[run] report: {run_dir / 'report.md'}")
    print(f"[run] crm:    {config.crm_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
