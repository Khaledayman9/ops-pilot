from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator.graph import IncidentOrchestrator
from app.api.deps import get_optional_user
from app.db.models import User
from app.db.postgres import get_db
from app.schemas.chat import ChatCreate, MessageCreate
from app.services.chat_service import ChatService
from logger import logger

router = APIRouter()
_orchestrator = IncidentOrchestrator()


@router.get(
    "/incident",
    summary="Stream incident analysis via Server-Sent Events",
    description=(
        "Opens an SSE connection and streams each agent step as it executes. "
        "Pass `session_id` to resume an existing chat, or omit to create a new one. "
        "Authentication is optional — unauthenticated requests use an anonymous session."
    ),
)
async def stream_incident(
    query: str = Query(..., description="Incident description"),
    session_id: str | None = Query(
        None, description="Existing session UUID (optional)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> EventSourceResponse:
    chat_svc = ChatService(db)
    user_id = current_user.id if current_user else None

    if not session_id:
        chat = await chat_svc.create_chat(ChatCreate(title=query[:80]), user_id=user_id)
        session_id = str(chat.id)

    await chat_svc.add_message(session_id, MessageCreate(role="user", content=query))

    async def generator():
        yield {"event": "session", "data": json.dumps({"session_id": session_id})}

        result_parts: list[str] = []
        async for event in _orchestrator.run_with_stream(query, session_id):
            yield {"event": event.event, "data": json.dumps(event.model_dump())}
            await chat_svc.record_execution(
                session_id,
                event.step or "unknown",
                event.status or "running",
                json.dumps(event.data) if event.data else None,
            )
            if event.event == "result":
                result_parts.append(json.dumps(event.data))

        if result_parts:
            await chat_svc.add_message(
                session_id,
                MessageCreate(role="assistant", content="\n".join(result_parts)),
            )

        yield {"event": "done", "data": json.dumps({"session_id": session_id})}
        logger.info(f"[Stream] Done session={session_id}")

    return EventSourceResponse(generator())
