"""Per-candidate moderation pipeline.

Per captured post:
    1. POST /api/council/moderate-lead -> structured review (LeadReview)
    2. If the review clears the approval gate (HOT + verified + high
       confidence + no trust_flags + not review_required):
         a. append to data/moderation/approved_leads.jsonl
         b. fire the configured n8n webhook (event=lead.approved)
    3. Otherwise: keep the verdict in the run results for the human
       reviewer (doctrine §00.4) — never auto-deliver below the gate.

`moderate_posts()` fans this out across many candidates with a thread
pool. No outreach is generated. Provenance > volume.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .config import ModerationConfig, get_config
from .council_client import CouncilClient, CouncilClientError
from .crm_store import evaluate_approval, save_approved
from .webhooks import emit_webhook

log = logging.getLogger("moderation.pipeline")


@dataclass
class ModerationResult:
    """Outcome of moderating a single captured post."""

    candidate_id: Optional[str]
    review: Optional[Dict[str, Any]] = None
    approval: Optional[Dict[str, Any]] = None
    approved: bool = False
    persisted: bool = False
    webhook_fired: bool = False
    error_kind: Optional[str] = None
    error_message: Optional[str] = None
    elapsed_ms: int = 0
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


@dataclass
class ModerationSummary:
    """Aggregate stats for one moderation batch."""

    total: int
    reviewed: int
    approved: int
    persisted: int
    webhooks_fired: int
    errors: int
    error_kinds: Dict[str, int] = field(default_factory=dict)
    temperature_counts: Dict[str, int] = field(default_factory=dict)
    results: List[ModerationResult] = field(default_factory=list)


def moderate_one(
    candidate: Dict[str, Any],
    *,
    client: CouncilClient,
    config: Optional[ModerationConfig] = None,
) -> ModerationResult:
    """Run the full per-candidate pipeline. Never raises."""
    config = config or client.config
    candidate_id = candidate.get("candidate_id")
    result = ModerationResult(candidate_id=candidate_id)

    # ---- Stage 1: council moderation -----------------------------------
    try:
        response = client.moderate_lead(candidate)
    except CouncilClientError as e:
        result.error_kind = e.kind
        result.error_message = str(e)
        log.warning(
            "moderate_call_failed candidate_id=%s kind=%s msg=%s",
            candidate_id, e.kind, e,
        )
        return result

    review = response.get("review") or {}
    upstream_error = response.get("error")
    result.review = review
    result.model = response.get("model")
    result.elapsed_ms = int(response.get("elapsed_ms") or 0)
    result.usage = response.get("usage")
    if upstream_error:
        result.error_kind = upstream_error.get("kind")
        result.error_message = upstream_error.get("message")
        log.warning(
            "moderate_upstream_error candidate_id=%s kind=%s",
            candidate_id, result.error_kind,
        )

    # ---- Stage 2: approval gate ----------------------------------------
    approval = evaluate_approval(review, config)
    result.approval = approval
    result.approved = bool(approval["approved"])
    if not result.approved:
        log.info(
            "moderate_below_gate candidate_id=%s reason=%s",
            candidate_id, approval["reason"],
        )
        return result

    # ---- Stage 3: persist + webhook ------------------------------------
    metadata = {"model": result.model, "elapsed_ms": result.elapsed_ms}
    try:
        save_approved(
            candidate, review,
            approval=approval, metadata=metadata, config=config,
        )
        result.persisted = True
    except OSError as e:
        log.error("moderate_save_failed candidate_id=%s err=%s", candidate_id, e)
        result.error_kind = result.error_kind or "store_write_error"
        result.error_message = result.error_message or str(e)

    if config.webhook_url:
        result.webhook_fired = emit_webhook(
            candidate, review,
            approval=approval, metadata=metadata, config=config,
        )

    return result


def moderate_posts(
    candidates: Iterable[Dict[str, Any]],
    *,
    config: Optional[ModerationConfig] = None,
    client: Optional[CouncilClient] = None,
) -> ModerationSummary:
    """Fan out moderation across `candidates`, respecting `max_concurrent`."""
    config = config or get_config()
    candidates = list(candidates)
    summary = ModerationSummary(
        total=len(candidates), reviewed=0, approved=0,
        persisted=0, webhooks_fired=0, errors=0,
    )
    if not candidates:
        return summary

    owns_client = client is None
    if client is None:
        client = CouncilClient(config)

    if config.fail_open:
        try:
            client.health()
        except CouncilClientError as e:
            log.warning(
                "council_unreachable fail_open=true kind=%s msg=%s",
                e.kind, e,
            )
            for c in candidates:
                summary.results.append(
                    ModerationResult(
                        candidate_id=c.get("candidate_id"),
                        error_kind=e.kind,
                        error_message=str(e),
                    )
                )
            summary.errors = len(candidates)
            summary.error_kinds[e.kind] = len(candidates)
            if owns_client:
                client.close()
            return summary

    max_workers = max(1, min(config.max_concurrent, len(candidates)))
    try:
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="moderate") as pool:
            futures = {
                pool.submit(moderate_one, c, client=client, config=config): c
                for c in candidates
            }
            for fut in as_completed(futures):
                result = fut.result()
                summary.results.append(result)
                if result.review is not None:
                    summary.reviewed += 1
                    temp = (result.review.get("lead_temperature") or "UNKNOWN").upper()
                    summary.temperature_counts[temp] = (
                        summary.temperature_counts.get(temp, 0) + 1
                    )
                if result.approved:
                    summary.approved += 1
                if result.persisted:
                    summary.persisted += 1
                if result.webhook_fired:
                    summary.webhooks_fired += 1
                if result.error_kind:
                    summary.errors += 1
                    summary.error_kinds[result.error_kind] = (
                        summary.error_kinds.get(result.error_kind, 0) + 1
                    )
    finally:
        if owns_client:
            client.close()

    log.info(
        "moderate_batch_complete total=%s reviewed=%s approved=%s persisted=%s webhooks=%s errors=%s",
        summary.total,
        summary.reviewed,
        summary.approved,
        summary.persisted,
        summary.webhooks_fired,
        summary.errors,
    )
    return summary
