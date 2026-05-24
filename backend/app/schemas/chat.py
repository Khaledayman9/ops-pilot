from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    title: str | None = None


class ChatResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    title: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    role: str
    content: str


class MessageResponse(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    role: str
    content: str
    timestamp: datetime
    model_config = {"from_attributes": True}
