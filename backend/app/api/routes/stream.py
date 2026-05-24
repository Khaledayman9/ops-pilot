import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.db.postgres import get_db
from app.agents.orchestrator.graph import IncidentOrchestrator
from app.schemas.chat import ChatCreate, MessageCreate
from app.services.chat_service import ChatService
from logger import logger

router = APIRouter()
_orchestrator = IncidentOrchestrator()


@router.get("/incident")
async def stream_incident(
    query: str = Query(...),
    session_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    chat_svc = ChatService(db)

    if not session_id:
        chat = await chat_svc.create_chat(ChatCreate(title=query[:80]))
        session_id = str(chat.id)

    await chat_svc.add_message(session_id, MessageCreate(role="user", content=query))

    async def generator():
        yield {"event": "session", "data": json.dumps({"session_id": session_id})}

        result_parts: list[str] = []
        async for event in _orchestrator.run_with_stream(query, session_id):
            yield {"event": event.event, "data": json.dumps(event.model_dump())}
            await chat_svc.record_execution(
                session_id, event.step or "unknown", event.status or "running",
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