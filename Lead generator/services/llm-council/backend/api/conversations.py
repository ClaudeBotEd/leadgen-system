"""/api/conversations — conversation CRUD + 3-stage council message endpoints."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from ..config import get_settings
from ..dependencies import limiter, require_api_token
from ..logging import get_logger
from ..schemas import (
    Conversation,
    ConversationMetadata,
    CreateConversationRequest,
    SendMessageRequest,
)
from ..services import council as council_svc
from ..services import storage

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
log = get_logger("api.conversations")


def _rate_limit() -> str:
    return f"{get_settings().rate_limit_per_minute}/minute"


@router.get("", response_model=list[ConversationMetadata])
async def list_conversations() -> list[ConversationMetadata]:
    items = await storage.list_conversations()
    return [ConversationMetadata(**i) for i in items]


@router.post("", response_model=Conversation, status_code=201)
async def create_conversation(req: CreateConversationRequest) -> Conversation:
    conv = await storage.create_conversation(
        str(uuid.uuid4()), title=req.title or "New Conversation"
    )
    return Conversation(**conv)


@router.get("/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str) -> Conversation:
    conv = await storage.require_conversation(conversation_id)
    return Conversation(**conv)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str) -> None:
    await storage.require_conversation(conversation_id)
    await storage.delete_conversation(conversation_id)


@router.post("/{conversation_id}/message")
@limiter.limit(_rate_limit)
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    request: Request,  # noqa: ARG001 — required by slowapi
    _=Depends(require_api_token),
) -> dict:
    """Run the full 3-stage council and return the complete result."""
    conv = await storage.require_conversation(conversation_id)
    is_first = len(conv["messages"]) == 0

    await storage.add_user_message(conversation_id, body.content)

    if is_first:
        title = await council_svc.generate_conversation_title(body.content)
        await storage.update_conversation_title(conversation_id, title)

    stage1, stage2, stage3, metadata = await council_svc.run_full_council(body.content)
    await storage.add_assistant_message(conversation_id, stage1, stage2, stage3, metadata)

    return {
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
        "metadata": metadata,
    }


@router.post("/{conversation_id}/message/stream")
@limiter.limit(_rate_limit)
async def send_message_stream(
    conversation_id: str,
    body: SendMessageRequest,
    request: Request,  # noqa: ARG001 — required by slowapi
    _=Depends(require_api_token),
) -> EventSourceResponse:
    """Stream the 3-stage council as Server-Sent Events."""
    conv = await storage.require_conversation(conversation_id)
    is_first = len(conv["messages"]) == 0

    async def event_generator():
        try:
            await storage.add_user_message(conversation_id, body.content)

            title_task = None
            if is_first:
                title_task = asyncio.create_task(
                    council_svc.generate_conversation_title(body.content)
                )

            yield {"event": "message", "data": json.dumps({"type": "stage1_start"})}
            stage1 = await council_svc.stage1_collect_responses(body.content)
            yield {
                "event": "message",
                "data": json.dumps({"type": "stage1_complete", "data": stage1}),
            }

            yield {"event": "message", "data": json.dumps({"type": "stage2_start"})}
            stage2, label_to_model = await council_svc.stage2_collect_rankings(
                body.content, stage1
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
            stage3 = await council_svc.stage3_synthesize_final(body.content, stage1, stage2)
            yield {
                "event": "message",
                "data": json.dumps({"type": "stage3_complete", "data": stage3}),
            }

            if title_task is not None:
                title = await title_task
                await storage.update_conversation_title(conversation_id, title)
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "title_complete", "data": {"title": title}}),
                }

            await storage.add_assistant_message(
                conversation_id, stage1, stage2, stage3,
                {"label_to_model": label_to_model, "aggregate_rankings": aggregate},
            )
            yield {"event": "message", "data": json.dumps({"type": "complete"})}

        except Exception as e:
            log.exception("stream_failed", error=str(e))
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "message": str(e)}),
            }

    return EventSourceResponse(event_generator())
