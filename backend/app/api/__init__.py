"""
API package — single aggregated router mounted in app/main.py.

All routes live under /api/v1 except /health (root level).

Route tree:
    GET  /health
    POST /api/v1/auth/register
    POST /api/v1/auth/login
    POST /api/v1/auth/refresh
    GET  /api/v1/auth/me
    POST /api/v1/incident/analyze
    GET  /api/v1/stream/incident
    POST /api/v1/chat/
    GET  /api/v1/chat/
    GET  /api/v1/chat/{session_id}
    GET  /api/v1/chat/{session_id}/messages
    GET  /api/v1/chat/{session_id}/executions
    DELETE /api/v1/chat/{session_id}
"""

from .routes import router

__all__ = ["router"]
