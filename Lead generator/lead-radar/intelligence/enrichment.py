"""Per-lead enrichment pipeline.

Per lead:
    1. Council score-lead -> structured intelligence
    2. (Optional) Council generate-sequence -> outreach drafts
    3. Persist to CRM JSONL (if lead_quality_score >= threshold)
    4. (Optional) Fire n8n webhook (if score >= webhook_min_score)

`enrich_leads()` fans this out across many leads with a thread pool.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .config import IntelligenceConfig, get_config
from .council_client import CouncilClient, CouncilClientError
from .crm_store import save_qualified
from .webhooks import emit_webhook

log = logging.getLogger("intelligence.enrichment")


@dataclass
class EnrichmentResult:
    """Outcome of enriching a single lead."""

    lead_id: Optional[str]
    intelligence: Optional[Dict[str, Any]] = None
    sequence: Optional[Dict[str, Any]] = None
    saved: bool = False
    webhook_fired: bool = False
    error_kind: Optional[str] = None
    error_message: Optional[str] = None
    elapsed_ms_score: int = 0
    elapsed_ms_sequence: int = 0
    model: Optional[str] = None
    score: int = 0
    score_usage: Optional[Dict[str, int]] = None
    sequence_usage: Optional[Dict[str, int]] = None


@dataclass
class EnrichmentSummary:
    """Aggregate stats for one enrichment batch."""

    total: int
    scored: int
    qualified: int
    persisted: int
    webhooks_fired: int
    errors: int
    error_kinds: Dict[str, int] = field(default_factory=dict)
    results: List[EnrichmentResult] = field(default_factory=list)


def _safe_get_score(intelligence: Dict[str, Any]) -> int:
    try:
        return int(intelligence.get("lead_quality_score") or 0)
    except (TypeError, ValueError):
        return 0


def enrich_one(
    lead: Dict[str, Any],
    *,
    client: CouncilClient,
    config: Optional[IntelligenceConfig] = None,
) -> EnrichmentResult:
    """Run the full per-lead pipeline. Never raises."""
    config = config or client.config
    lead_id = lead.get("lead_id")
    result = EnrichmentResult(lead_id=lead_id)

    # ---- Stage 1: scoring ------------------------------------------------
    try:
        score_resp = client.score_lead(lead)
    except CouncilClientError as e:
        result.error_kind = e.kind
        result.error_message = str(e)
        log.warning(
            "enrich_score_failed lead_id=%s kind=%s msg=%s",
            lead_id, e.kind, e,
        )
        return result

    intelligence = score_resp.get("intelligence") or {}
    upstream_error = score_resp.get("error")
    result.intelligence = intelligence
    result.model = score_resp.get("model")
    result.elapsed_ms_score = int(score_resp.get("elapsed_ms") or 0)
    result.score = _safe_get_score(intelligence)
    result.score_usage = score_resp.get("usage")
    if upstream_error:
        result.error_kind = upstream_error.get("kind")
        result.error_message = upstream_error.get("message")
        log.warning(
            "enrich_score_upstream_error lead_id=%s kind=%s",
            lead_id, result.error_kind,
        )

    # ---- Threshold gate --------------------------------------------------
    if result.score < config.quality_threshold:
        log.info(
            "enrich_below_threshold lead_id=%s score=%s threshold=%s",
            lead_id, result.score, config.quality_threshold,
        )
        return result

    # ---- Stage 2: outreach sequence -------------------------------------
    sequence: Optional[Dict[str, Any]] = None
    if config.generate_sequence:
        try:
            seq_resp = client.generate_sequence(lead, intelligence)
            sequence = seq_resp.get("sequence") or {}
            result.elapsed_ms_sequence = int(seq_resp.get("elapsed_ms") or 0)
            result.sequence_usage = seq_resp.get("usage")
            if seq_resp.get("error"):
                err = seq_resp["error"]
                log.warning(
                    "enrich_sequence_upstream_error lead_id=%s kind=%s",
                    lead_id, err.get("kind"),
                )
                sequence = None
        except CouncilClientError as e:
            log.warning(
                "enrich_sequence_failed lead_id=%s kind=%s msg=%s",
                lead_id, e.kind, e,
            )
            sequence = None
    result.sequence = sequence

    # ---- Stage 3: persist + webhook -------------------------------------
    metadata = {
        "model": result.model,
        "score_elapsed_ms": result.elapsed_ms_score,
        "sequence_elapsed_ms": result.elapsed_ms_sequence,
    }
    try:
        save_qualified(lead, intelligence, sequence, metadata=metadata, config=config)
        result.saved = True
    except OSError as e:
        log.error("enrich_save_failed lead_id=%s err=%s", lead_id, e)
        result.error_kind = result.error_kind or "crm_write_error"
        result.error_message = result.error_message or str(e)

    if config.webhook_url:
        result.webhook_fired = emit_webhook(
            lead, intelligence, sequence, metadata=metadata, config=config
        )

    return result


def enrich_leads(
    leads: Iterable[Dict[str, Any]],
    *,
    config: Optional[IntelligenceConfig] = None,
    client: Optional[CouncilClient] = None,
) -> EnrichmentSummary:
    """Fan out enrichment across `leads`, respecting `max_concurrent`.

    Returns an aggregate summary. Individual lead errors are captured in
    `summary.results[i].error_*` and never raised; if the council itself
    is unreachable and `fail_open` is set, the batch is short-circuited
    with one error per lead rather than crashing the scrape pipeline.
    """
    config = config or get_config()
    leads = list(leads)
    summary = EnrichmentSummary(
        total=len(leads),
        scored=0,
        qualified=0,
        persisted=0,
        webhooks_fired=0,
        errors=0,
    )
    if not leads:
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
            for lead in leads:
                summary.results.append(
                    EnrichmentResult(
                        lead_id=lead.get("lead_id"),
                        error_kind=e.kind,
                        error_message=str(e),
                    )
                )
            summary.errors = len(leads)
            summary.error_kinds[e.kind] = len(leads)
            if owns_client:
                client.close()
            return summary

    max_workers = max(1, min(config.max_concurrent, len(leads)))
    try:
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="enrich") as pool:
            futures = {
                pool.submit(enrich_one, lead, client=client, config=config): lead
                for lead in leads
            }
            for fut in as_completed(futures):
                result = fut.result()
                summary.results.append(result)
                if result.intelligence is not None:
                    summary.scored += 1
                if result.saved:
                    summary.qualified += 1
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
        "enrich_batch_complete total=%s scored=%s qualified=%s persisted=%s webhooks=%s errors=%s",
        summary.total,
        summary.scored,
        summary.qualified,
        summary.persisted,
        summary.webhooks_fired,
        summary.errors,
    )
    return summary
