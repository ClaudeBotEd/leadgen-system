"""Conversation persistence layer (async SQLAlchemy)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from ..db.database import session_scope
from ..db.models import Conversation as ConversationRow
from ..db.models import Message as MessageRow
from ..errors import ConversationNotFoundError


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _serialize_message(row: MessageRow) -> Dict[str, Any]:
    if row.role == "assistant" and row.stage_payload:
        payload = row.stage_payload
        return {
            "role": "assistant",
            "stage1": payload.get("stage1", []),
            "stage2": payload.get("stage2", []),
            "stage3": payload.get("stage3", {}),
            "metadata": payload.get("metadata", {}),
            "created_at": _iso(row.created_at),
        }
    return {
        "role": row.role,
        "content": row.content or "",
        "created_at": _iso(row.created_at),
    }


def _serialize_conversation(row: ConversationRow) -> Dict[str, Any]:
    return {
        "id": row.id,
        "created_at": _iso(row.created_at),
        "title": row.title,
        "messages": [_serialize_message(m) for m in row.messages],
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_conversation(
    conversation_id: str, title: str = "New Conversation"
) -> Dict[str, Any]:
    async with session_scope() as session:
        row = ConversationRow(id=conversation_id, title=title)
        session.add(row)
        await session.flush()
        return {
            "id": row.id,
            "created_at": _iso(row.created_at),
            "title": row.title,
            "messages": [],
        }


async def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    async with session_scope() as session:
        stmt = (
            select(ConversationRow)
            .where(ConversationRow.id == conversation_id)
            .options(selectinload(ConversationRow.messages))
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        return _serialize_conversation(row) if row else None


async def require_conversation(conversation_id: str) -> Dict[str, Any]:
    conv = await get_conversation(conversation_id)
    if conv is None:
        raise ConversationNotFoundError(
            f"Conversation {conversation_id} not found",
            details={"conversation_id": conversation_id},
        )
    return conv


async def list_conversations() -> List[Dict[str, Any]]:
    async with session_scope() as session:
        stmt = (
            select(ConversationRow)
            .options(selectinload(ConversationRow.messages))
            .order_by(ConversationRow.created_at.desc())
        )
        rows = (await session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "created_at": _iso(r.created_at),
                "title": r.title,
                "message_count": len(r.messages),
            }
            for r in rows
        ]


async def add_user_message(conversation_id: str, content: str) -> None:
    async with session_scope() as session:
        exists = await session.get(ConversationRow, conversation_id)
        if exists is None:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found",
                details={"conversation_id": conversation_id},
            )
        session.add(
            MessageRow(
                conversation_id=conversation_id, role="user", content=content
            )
        )


async def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    async with session_scope() as session:
        exists = await session.get(ConversationRow, conversation_id)
        if exists is None:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found",
                details={"conversation_id": conversation_id},
            )
        session.add(
            MessageRow(
                conversation_id=conversation_id,
                role="assistant",
                content=None,
                stage_payload={
                    "stage1": stage1,
                    "stage2": stage2,
                    "stage3": stage3,
                    "metadata": metadata or {},
                },
            )
        )


async def update_conversation_title(conversation_id: str, title: str) -> None:
    async with session_scope() as session:
        row = await session.get(ConversationRow, conversation_id)
        if row is None:
            raise ConversationNotFoundError(
                f"Conversation {conversation_id} not found",
                details={"conversation_id": conversation_id},
            )
        row.title = title[:200]


async def delete_conversation(conversation_id: str) -> bool:
    async with session_scope() as session:
        result = await session.execute(
            delete(ConversationRow).where(ConversationRow.id == conversation_id)
        )
        return result.rowcount > 0
