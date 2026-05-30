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
from app.db.models import Chat
import uuid
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
    document_filenames: str | None = Query(
        None, description="Comma-separated original filenames of uploaded documents"
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

    if session_id:
        existing = await chat_svc.get_chat(session_id, user_id=user_id)
        if not existing:
            new_chat = Chat(
                id=uuid.UUID(session_id),
                user_id=user_id,
                title=safe_query[:80],
            )
            db.add(new_chat)
            await db.commit()
            await db.refresh(new_chat)
    else:
        chat = await chat_svc.create_chat(ChatCreate(title=safe_query[:80]), user_id=user_id)
        session_id = str(chat.id)

    message_content = safe_query
    if safe_document_context:
        message_content = (
            f"{safe_query}\n\n=== Uploaded Document Context ===\n{safe_document_context}"
        )

    await chat_svc.add_message(session_id, MessageCreate(role="user", content=message_content))

    prior_messages = await chat_svc.get_messages(session_id)
    history_dicts = [{"role": m.role, "content": m.content} for m in prior_messages[:-1]]

    parsed_filenames = (
        [f.strip() for f in document_filenames.split(",") if f.strip()]
        if document_filenames
        else []
    )

    async def generator():
        yield {"event": "session", "data": json.dumps({"session_id": session_id})}

        result_data: dict = {}
        enabled = set(enabled_agents.split(",")) if enabled_agents else None
        if safe_document_context:
            enabled = (enabled or set()) | {"document_processor"}
        orchestrator = IncidentOrchestrator()
        async for event in orchestrator.run_with_stream(
            safe_query,
            session_id,
            document_context=safe_document_context,
            document_filenames=parsed_filenames,
            enabled_agents=enabled,
            chat_history=history_dicts,
        ):
            yield {"event": event.event, "data": json.dumps(event.model_dump())}
            await chat_svc.record_execution(
                session_id,
                event.step or "unknown",
                event.status or "running",
                json.dumps(event.data) if event.data else None,
            )
            if event.event == "result":
                result_data = event.data if isinstance(event.data, dict) else {}

        if result_data:
            natural = result_data.get("natural_response", "")
            summary = result_data.get("conversation_summary", "")
            assistant_content = json.dumps(
                {
                    "natural_response": natural,
                    "conversation_summary": summary,
                    "is_incident_relevant": result_data.get("is_incident_relevant", True),
                }
            )
            await chat_svc.add_message(
                session_id,
                MessageCreate(role="assistant", content=assistant_content),
            )

        yield {"event": "done", "data": json.dumps({"session_id": session_id})}
        logger.info(f"[Stream] Done session={session_id}")

    return EventSourceResponse(generator())
