import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chat, Message, AgentExecution
from app.schemas.chat import ChatCreate, ChatResponse, MessageCreate, MessageResponse
from logger import logger


class ChatService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_chat(self, payload: ChatCreate) -> ChatResponse:
        chat = Chat(user_id=payload.user_id, title=payload.title)
        self._db.add(chat)
        await self._db.commit()
        await self._db.refresh(chat)
        logger.info(f"[ChatService] Created chat {chat.id}")
        return ChatResponse.model_validate(chat)

    async def get_chat(self, session_id: str) -> ChatResponse | None:
        result = await self._db.execute(select(Chat).where(Chat.id == uuid.UUID(session_id)))
        chat = result.scalar_one_or_none()
        return ChatResponse.model_validate(chat) if chat else None

    async def list_chats(self, user_id: str = "anonymous") -> list[ChatResponse]:
        result = await self._db.execute(
            select(Chat).where(Chat.user_id == user_id).order_by(Chat.created_at.desc())
        )
        return [ChatResponse.model_validate(c) for c in result.scalars().all()]

    async def add_message(self, session_id: str, payload: MessageCreate) -> MessageResponse:
        msg = Message(chat_id=uuid.UUID(session_id), role=payload.role, content=payload.content)
        self._db.add(msg)
        await self._db.commit()
        await self._db.refresh(msg)
        return MessageResponse.model_validate(msg)

    async def get_messages(self, session_id: str) -> list[MessageResponse]:
        result = await self._db.execute(
            select(Message)
            .where(Message.chat_id == uuid.UUID(session_id))
            .order_by(Message.timestamp.asc())
        )
        return [MessageResponse.model_validate(m) for m in result.scalars().all()]

    async def record_execution(
        self, session_id: str, step_name: str, status: str, payload: str | None = None
    ) -> None:
        ex = AgentExecution(
            chat_id=uuid.UUID(session_id),
            step_name=step_name,
            status=status,
            payload=payload,
        )
        self._db.add(ex)
        await self._db.commit()

    async def get_executions(self, session_id: str) -> list[dict]:
        result = await self._db.execute(
            select(AgentExecution)
            .where(AgentExecution.chat_id == uuid.UUID(session_id))
            .order_by(AgentExecution.timestamp.asc())
        )
        return [
            {"id": str(e.id), "step_name": e.step_name, "status": e.status,
             "payload": e.payload, "timestamp": e.timestamp.isoformat()}
            for e in result.scalars().all()
        ]