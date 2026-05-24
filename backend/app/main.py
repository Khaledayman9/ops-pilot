"""
FastAPI application factory.

Route structure (all under /api/v1):
    /health
    /api/v1/auth/*
    /api/v1/incident/*
    /api/v1/chat/*
    /api/v1/stream/*
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
        description="AI-powered DevOps Incident Response & Root Cause Analysis",
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

    # Global error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    # Mount routers
    app.include_router(api_router)

    return app


app = create_app()
