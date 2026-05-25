from __future__ import annotations

import json
import uuid as _uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator.graph import IncidentOrchestrator
from app.core.guardrails import GuardrailViolation, apply_all as apply_guardrails
from app.schemas.chat import ChatCreate, MessageCreate
from app.schemas.incident import IncidentRequest, IncidentResponse
from app.services.chat_service import ChatService

__all__ = ["IncidentService"]


class IncidentService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._orchestrator = IncidentOrchestrator()
        self._chat = ChatService(db)

    async def analyze(
        self,
        request: IncidentRequest,
        user_id: str | None = None,
    ) -> IncidentResponse:
        # Guardrails
        try:
            safe_query = apply_guardrails(request.query)
        except GuardrailViolation as e:
            raise e

        uid = _uuid.UUID(user_id) if user_id else None
        session_id = request.session_id
        if not session_id:
            chat = await self._chat.create_chat(ChatCreate(title=safe_query[:80]), user_id=uid)
            session_id = str(chat.id)

        await self._chat.add_message(session_id, MessageCreate(role="user", content=safe_query))

        final_data: dict = {}
        async for event in self._orchestrator.run_with_stream(safe_query, session_id):
            await self._chat.record_execution(
                session_id,
                event.step or "unknown",
                event.status or "running",
                json.dumps(event.data) if event.data else None,
            )
            if event.event == "result":
                final_data = event.data or {}  # type: ignore[assignment]

        await self._chat.add_message(
            session_id,
            MessageCreate(role="assistant", content=json.dumps(final_data)),
        )

        return IncidentResponse(
            session_id=session_id,
            classification=final_data.get("classification", {}),
            graph_context=final_data.get("graph_context", {}),
            root_cause=final_data.get("root_cause", ""),
            blast_radius=final_data.get("blast_radius", {}),
            remediation_steps=final_data.get("remediation_steps", []),
            timeline=final_data.get("timeline", []),
        )
