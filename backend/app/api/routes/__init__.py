"""
Routes package — imported exclusively by app/api/__init__.py.

Route tree:
    GET    /health
    POST   /api/v1/auth/register
    POST   /api/v1/auth/login
    POST   /api/v1/auth/refresh
    GET    /api/v1/auth/me
    POST   /api/v1/incident/analyze
    GET    /api/v1/stream/incident
    POST   /api/v1/chat/
    GET    /api/v1/chat/
    GET    /api/v1/chat/{session_id}
    GET    /api/v1/chat/{session_id}/messages
    GET    /api/v1/chat/{session_id}/executions
    DELETE /api/v1/chat/{session_id}
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .chat import router as chat_router
from .health import router as health_router
from .incident import router as incident_router
from .stream import router as stream_router
from .settings import router as settings_router

# Root router
router = APIRouter()

# No-prefix, no-auth routes
router.include_router(health_router)

# Versioned group
v1 = APIRouter(prefix="/api/v1")
v1.include_router(auth_router, prefix="/auth", tags=["auth"])
v1.include_router(incident_router, prefix="/incident", tags=["incident"])
v1.include_router(chat_router, prefix="/chat", tags=["chat"])
v1.include_router(stream_router, prefix="/stream", tags=["stream"])
v1.include_router(settings_router, prefix="/settings", tags=["settings"])

router.include_router(v1)

__all__ = ["router"]
