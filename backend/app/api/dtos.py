"""
Data Transfer Objects (DTOs) — request/response shapes used directly in route handlers.

These are thin wrappers or re-exports of schema models.
Keep route handlers free of raw dict construction.
"""

from __future__ import annotations

from app.schemas.auth import RefreshRequest, TokenResponse, UserCreate, UserLogin, UserPublic
from app.schemas.chat import ChatCreate, ChatResponse, MessageResponse
from app.schemas.incident import IncidentRequest, IncidentResponse
from app.schemas.stream import StreamEvent

__all__ = [
    # Auth
    "UserCreate",
    "UserLogin",
    "UserPublic",
    "TokenResponse",
    "RefreshRequest",
    # Chat
    "ChatCreate",
    "ChatResponse",
    "MessageResponse",
    # Incident
    "IncidentRequest",
    "IncidentResponse",
    # Stream
    "StreamEvent",
]
