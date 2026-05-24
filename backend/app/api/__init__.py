"""
API package — exposes a single ``router`` that aggregates all sub-routers.

Mount it in ``app/main.py`` with:

    from app.api import router as api_router
    app.include_router(api_router)
"""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.incident import router as incident_router
from app.api.routes.stream import router as stream_router

__all__ = ["router"]

# Root router
router = APIRouter()

# Health — no prefix, no auth required
router.include_router(health_router)

# Versioned API group
v1 = APIRouter(prefix="/api/v1")
v1.include_router(auth_router, prefix="/auth", tags=["auth"])
v1.include_router(incident_router, prefix="/incident", tags=["incident"])
v1.include_router(chat_router, prefix="/chat", tags=["chat"])
v1.include_router(stream_router, prefix="/stream", tags=["stream"])

router.include_router(v1)
