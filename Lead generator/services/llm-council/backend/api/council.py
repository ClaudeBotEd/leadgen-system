"""/api/council — generic + lead-generation council endpoints.

These endpoints are the integration surface for n8n, CRM, outreach automation,
and lead-radar scoring pipelines.
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
    AnalyzeLeadRequest,
    CouncilMetadata,
    CouncilOutput,
    CouncilQueryRequest,
    GenerateOutreachRequest,
    ModelResponse,
    RankingResponse,
    ReviewScrapeRequest,
)
from ..services import council as council_svc
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
# Lead-domain endpoints
# ---------------------------------------------------------------------------


@router.post("/analyze-lead")
@limiter.limit(_rate_limit)
async def analyze_lead(
    body: AnalyzeLeadRequest,
    request: Request,  # noqa: ARG001
    _=Depends(require_api_token),
) -> dict:
    """Council-grade qualification analysis for a single lead record."""
    prompt = council_svc.build_analyze_lead_prompt(
        body.lead.model_dump(), body.objective, body.locale
    )
    stage1, stage2, stage3, metadata = await council_svc.run_full_council(prompt)
    return _to_output(stage1, stage2, stage3, metadata).model_dump()


@router.post("/generate-outreach")
@limiter.limit(_rate_limit)
async def generate_outreach(
    body: GenerateOutreachRequest,
    request: Request,  # noqa: ARG001
    _=Depends(require_api_token),
) -> dict:
    """Council-drafted outreach message (email / linkedin / sms)."""
    prompt = council_svc.build_outreach_prompt(
        body.lead.model_dump(),
        body.angle,
        body.channel,
        body.locale,
        body.tone,
        body.max_length_chars,
    )
    stage1, stage2, stage3, metadata = await council_svc.run_full_council(prompt)
    return _to_output(stage1, stage2, stage3, metadata).model_dump()


@router.post("/review-scrape")
@limiter.limit(_rate_limit)
async def review_scrape(
    body: ReviewScrapeRequest,
    request: Request,  # noqa: ARG001
    _=Depends(require_api_token),
) -> dict:
    """Quality review for a scraped sample. Returns structured QA report."""
    prompt = council_svc.build_review_scrape_prompt(
        body.sample, body.source_name, body.criteria
    )
    stage1, stage2, stage3, metadata = await council_svc.run_full_council(prompt)
    return _to_output(stage1, stage2, stage3, metadata).model_dump()
