"""
API package — single aggregated router mounted in app/main.py.
Imports from routes package which wires all sub-routers.
"""

from app.api.routes import router

__all__ = ["router"]
