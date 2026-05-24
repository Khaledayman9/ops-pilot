import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, incident, stream, health
from logger import logger


def create_app() -> FastAPI:
    app = FastAPI(
        title="Ops-Pilot",
        description="AI-powered DevOps Incident Response & Root Cause Analysis",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_tracing(request: Request, call_next):
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        logger.info(f"[{trace_id}] {request.method} {request.url.path}")
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(health.router, tags=["health"])
    app.include_router(incident.router, prefix="/api/incident", tags=["incident"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(stream.router, prefix="/api/stream", tags=["stream"])

    return app


app = create_app()