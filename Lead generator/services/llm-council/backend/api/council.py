"""/api/council — moderation + generic council endpoints.

The council is a *moderation and verification* layer for public homeowner
intent. The B2B-SaaS endpoints (analyze-lead, generate-outreach, score-lead,
generate-sequence) were removed in the trust-provenance refactor; they
conflicted with the doctrine (no AI-leadgen framing, no marketplace framing,
no outreach generation).

Remaining surface:
    POST /api/council/query              — generic 3-stage prompt
    POST /api/council/query/stream       — SSE variant
    POST /api/council/review-scrape      — source-quality QA (provenance-focused)
    POST /api/council/moderate-lead      — structured verdict on a captured post
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from ..config import get_settings
from ..dependencies import limiter, require_api_token
from ..logging import get_logger
from ..schemas import (
    AggregateRanking,
    CouncilMetadata,
    CouncilOutput,
    CouncilQueryRequest,
    ModerateLeadRequest,
    ModerateLeadResponse,
    ModelResponse,
    RankingResponse,
    ReviewScrapeRequest,
)
from ..services import council as council_svc
from ..services import lead_moderation
from ..services import storage

router = APIRouter(prefix="/api/council", tags=["council"])
log = get_logger("api.council")


def _rate_limit() -> str:
    return f"{get_settings().rate_limit_per_minute}/minute"


def _to_output(stage1, stage2, stage3, metadata) -> CouncilOutput:
    return CouncilOutput(
        stage1=[ModelResponse(**r) for r in stage1],
        stage2=[RankingResponse(**r) for r in stage2],
        stage3=ModelResponse(**stage3),
        metadata=CouncilMetadata(
            label_to_model=metadata.get("label_to_model", {}),
            aggregate_rankings=[
                AggregateRanking(**a) for a in metadata.get("aggregate_rankings", [])
            ],
        ),
    )


async def _run_and_optionally_persist(prompt: str, persist: bool, title_seed: str) -> dict:
    if persist:
        conv_id = str(uuid.uuid4())
        await storage.create_conversation(
            conv_id, title=(title_seed or "Council run")[:60]
        )
        await storage.add_user_message(conv_id, prompt)
        stage1, stage2, stage3, metadata = await council_svc.run_full_council(prompt)
        await storage.add_assistant_message(conv_id, stage1, stage2, stage3, metadata)
        return {
            "conversation_id": conv_id,
            "result": _to_output(stage1, stage2, stage3, metadata).model_dump(),
        }
    stage1, stage2, stage3, metadata = await council_svc.run_full_council(prompt)
    return {
        "conversation_id": None,
        "result": _to_output(stage1, stage2, stage3, metadata).model_dump(),
    }


# ---------------------------------------------------------------------------
# Generic query
# ---------------------------------------------------------------------------


@router.post("/query")
@limiter.limit(_rate_limit)
async def council_query(
    body: CouncilQueryRequest,
    request: Request,  # noqa: ARG001 — required by slowapi
    _=Depends(require_api_token),
) -> dict:
    """Run any prompt through the full 3-stage council."""
    log.info("council_query", persist=body.persist, query_len=len(body.query))
    return await _run_and_optionally_persist(
        body.query, body.persist, title_seed=body.query
    )


@router.post("/query/stream")
@limiter.limit(_rate_limit)
async def council_query_stream(
    body: CouncilQueryRequest,
    request: Request,  # noqa: ARG001 — required by slowapi
    _=Depends(require_api_token),
) -> EventSourceResponse:
    """Stream the 3-stage council for an ad-hoc prompt (no conversation required)."""

    async def gen():
        try:
            yield {"event": "message", "data": json.dumps({"type": "stage1_start"})}
            stage1 = await council_svc.stage1_collect_responses(body.query)
            yield {
                "event": "message",
                "data": json.dumps({"type": "stage1_complete", "data": stage1}),
            }

            yield {"event": "message", "data": json.dumps({"type": "stage2_start"})}
            stage2, label_to_model = await council_svc.stage2_collect_rankings(
                body.query, stage1
            )
            aggregate = council_svc.calculate_aggregate_rankings(stage2, label_to_model)
            yield {
                "event": "message",
                "data": json.dumps(
                    {
                        "type": "stage2_complete",
                        "data": stage2,
                        "metadata": {
                            "label_to_model": label_to_model,
                            "aggregate_rankings": aggregate,
                        },
                    }
                ),
            }

            yield {"event": "message", "data": json.dumps({"type": "stage3_start"})}
            stage3 = await council_svc.stage3_synthesize_final(body.query, stage1, stage2)
            yield {
                "event": "message",
                "data": json.dumps({"type": "stage3_complete", "data": stage3}),
            }

            yield {"event": "message", "data": json.dumps({"type": "complete"})}
        except Exception as e:
            log.exception("council_query_stream_failed", error=str(e))
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "message": str(e)}),
            }

    return EventSourceResponse(gen())


# ---------------------------------------------------------------------------
# Source-quality review (content-agnostic)
# ---------------------------------------------------------------------------


@router.post("/review-scrape")
@limiter.limit(_rate_limit)
async def review_scrape(
    body: ReviewScrapeRequest,
    request: Request,  # noqa: ARG001
    _=Depends(require_api_token),
) -> dict:
    """Provenance / source-quality review for a scraped sample."""
    prompt = council_svc.build_review_scrape_prompt(
        body.sample, body.source_name, body.criteria
    )
    stage1, stage2, stage3, metadata = await council_svc.run_full_council(prompt)
    return _to_output(stage1, stage2, stage3, metadata).model_dump()


# ---------------------------------------------------------------------------
# Lead moderation — provenance + intent verification on a single post
# ---------------------------------------------------------------------------


@router.post("/moderate-lead", response_model=ModerateLeadResponse)
@limiter.limit(_rate_limit)
async def moderate_lead(
    body: ModerateLeadRequest,
    request: Request,  # noqa: ARG001
    _=Depends(require_api_token),
) -> ModerateLeadResponse:
    """Moderate a single captured public post.

    Returns a structured verdict (HOT/WARM/OPP + provenance status + trust
    flags + reviewer-explainability fields). This is a *recommendation* —
    the accountable human reviewer assigns the final delivery band.
    """
    candidate = body.candidate.model_dump()
    result = await lead_moderation.moderate_lead(
        candidate,
        locale=body.locale,
        strategy=body.strategy,
        use_cache=body.use_cache,
    )
    log.info(
        "moderate_lead_api",
        candidate_id=candidate.get("candidate_id"),
        source_url=candidate.get("source_url"),
        temperature=result["review"]["lead_temperature"],
        provenance=result["review"]["provenance_status"],
        strategy=body.strategy,
        json_parsed=result["json_parsed"],
    )
    return ModerateLeadResponse(**result)
