from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.schemas.chat import ChatCreate, ChatResponse, MessageCreate, MessageResponse
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("/new", response_model=ChatResponse)
async def create_chat(payload: ChatCreate, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    return await ChatService(db).create_chat(payload)


@router.get("/{session_id}", response_model=ChatResponse)
async def get_chat(session_id: str, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    chat = await ChatService(db).get_chat(session_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str, db: AsyncSession = Depends(get_db)) -> list[MessageResponse]:
    return await ChatService(db).get_messages(session_id)


@router.get("/{session_id}/executions")
async def get_executions(session_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    return await ChatService(db).get_executions(session_id)


@router.get("/list/{user_id}", response_model=list[ChatResponse])
async def list_chats(user_id: str = "anonymous", db: AsyncSession = Depends(get_db)) -> list[ChatResponse]:
    return await ChatService(db).list_chats(user_id)