from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agents.orchestrator.graph import IncidentOrchestrator
from app.api.deps import get_optional_user
from app.api.uris import StreamURIs
from app.core.guardrails import GuardrailViolation, apply_all as apply_guardrails
from app.db.models import User
from app.db.postgres import get_db
from app.schemas.chat import ChatCreate, MessageCreate
from app.services.chat_service import ChatService
from logger import logger

router = APIRouter()


@router.get(
    StreamURIs.INCIDENT,
    summary="Stream incident analysis via Server-Sent Events",
    description=(
        "Opens an SSE connection that emits agent steps in real time. "
        "Each event has an event type: step | graph | reasoning | result | error | done."
    ),
)
async def stream_incident(
    query: str = Query(..., description="Raw incident description"),
    session_id: str | None = Query(None, description="Existing session UUID"),
    document_context: str | None = Query(
        None, description="Markdown converted from uploaded documents"
    ),
    enabled_agents: str | None = Query(None, description="Comma-separated enabled agent keys"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> EventSourceResponse:
    try:
        safe_query = apply_guardrails(query)
        safe_document_context = apply_guardrails(document_context or "") if document_context else ""
    except GuardrailViolation as e:
        error_detail = str(e)

        async def _error_gen():
            yield {
                "event": "error_event",
                "data": json.dumps({"detail": error_detail, "code": "GUARDRAIL_VIOLATION"}),
            }

        return EventSourceResponse(_error_gen())

    chat_svc = ChatService(db)
    user_id = current_user.id if current_user else None

    if not session_id:
        chat = await chat_svc.create_chat(ChatCreate(title=safe_query[:80]), user_id=user_id)
        session_id = str(chat.id)

    message_content = safe_query
    if safe_document_context:
        message_content = (
            f"{safe_query}\n\n=== Uploaded Document Context ===\n{safe_document_context}"
        )

    await chat_svc.add_message(session_id, MessageCreate(role="user", content=message_content))

    async def generator():
        yield {"event": "session", "data": json.dumps({"session_id": session_id})}

        result_parts: list[str] = []
        enabled = set(enabled_agents.split(",")) if enabled_agents else None
        orchestrator = IncidentOrchestrator()
        async for event in orchestrator.run_with_stream(
            safe_query,
            session_id,
            document_context=safe_document_context,
            enabled_agents=enabled,
        ):
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
