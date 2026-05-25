"""
FastAPI application factory.

Mounts the single aggregated router from app/api/__init__.py.
All business logic lives in services; routes are thin.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router as api_router
from logger import logger
from settings import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ops-Pilot",
        description=(
            "AI-powered multi-agent DevOps incident response platform. "
            "5 agents → Neo4j graph traversal → root cause → remediation."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request tracing
    @app.middleware("http")
    async def request_tracing(request: Request, call_next):
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        logger.info(f"[{trace_id}] {request.method} {request.url.path}")
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        trace_id = getattr(request.state, "trace_id", "unknown")
        logger.error(
            f"[{trace_id}] Unhandled exception on {request.url.path}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "trace_id": trace_id,
                "path": str(request.url.path),
            },
        )

    # Routers
    app.include_router(api_router)

    return app


app = create_app()
