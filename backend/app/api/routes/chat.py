from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.dtos import ChatCreate, ChatResponse, MessageResponse
from app.api.uris import ChatURIs
from app.db.models import User
from app.db.postgres import get_db
from app.services.chat_service import ChatService

router = APIRouter()


@router.post(
    ChatURIs.ROOT,
    response_model=ChatResponse,
    status_code=201,
    summary="Create a new chat session",
)
async def create_chat(
    payload: ChatCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    return await ChatService(db).create_chat(payload, user_id=current_user.id)


@router.get(
    ChatURIs.ROOT,
    response_model=list[ChatResponse],
    summary="List my chat sessions",
)
async def list_chats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatResponse]:
    return await ChatService(db).list_chats(user_id=current_user.id)


@router.get(
    ChatURIs.SESSION,
    response_model=ChatResponse,
    summary="Get a specific chat session",
)
async def get_chat(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    chat = await ChatService(db).get_chat(str(session_id), user_id=current_user.id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat


@router.get(
    ChatURIs.MESSAGES,
    response_model=list[MessageResponse],
    summary="Get all messages in a session",
)
async def get_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageResponse]:
    return await ChatService(db).get_messages(str(session_id))


@router.get(
    ChatURIs.EXECUTIONS,
    response_model=list[dict],
    summary="Get agent execution trace",
)
async def get_executions(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return await ChatService(db).get_executions(str(session_id))


@router.delete(
    ChatURIs.SESSION,
    # NOTE: 204 must NOT have a response_model — FastAPI enforces this
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
)
async def delete_chat(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    await ChatService(db).delete_chat(str(session_id), user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
