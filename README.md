# ⚡ Ops-Pilot — AI DevOps Incident Response Platform

AI-powered multi-agent incident response. Five specialized agents traverse
a Neo4j knowledge graph, perform root cause analysis, and stream a structured
remediation plan in real time.

## Architecture

    ┌─────────────────────────────────────────────────────────┐
    │  Next.js 14  │  Framer Motion  │  React Flow  │ Zustand │
    │  /login  /register  /  /chat                           │
    └──────────────────────┬──────────────────────────────────┘
                           │  SSE + REST  (JWT Bearer)
    ┌──────────────────────▼──────────────────────────────────┐
    │  FastAPI  /api/v1/{auth,incident,chat,stream}           │
    │  JWT (access + refresh)  │  bcrypt  │  Guardrails       │
    └──────────────┬──────────────────────────────────────────┘
                   │
    ┌──────────────▼──────────────────────────────────────────┐
    │  IncidentOrchestrator (LangGraph-style)                 │
    │  1. ClassifierAgent                                     │
    │  2. EntityExtractorAgent  (renamed from SearcherAgent)  │
    │  3. GraphAnalyzerAgent    ← DEEP Neo4j traversal        │
    │  4. WebSearcherAgent      ← DuckDuckGo intelligence     │
    │  5. IncidentAnalysisCrew  ← CrewAI 2-agent enrichment   │
    │  6. RootCauseFinderAgent                                │
    │  7. RemediatorAgent                                     │
    └──────┬────────────────────────────────────────────────--┘
           │
    ┌──────┴──────────┬──────────────────┬────────────────────┐
    │  Neo4j 5        │  PostgreSQL 16   │  Redis 7           │
    │  Knowledge      │  Users/Chat/     │  Celery broker     │
    │  Graph          │  Executions      │  + result backend  │
    └─────────────────┴──────────────────┴────────────────────┘

## Tech Stack

| Layer       | Technology                                          |
|-------------|-----------------------------------------------------|
| Frontend    | Next.js 14, TypeScript, Tailwind, Framer Motion, React Flow, Zustand, anime.js, Jest |
| Backend     | Python 3.11, FastAPI, LangGraph, CrewAI, LangChain  |
| LLM         | OpenAI (default) / Anthropic / Google — switchable via LLM_PROVIDER env var |
| Graph DB    | Neo4j 5 — service dependency knowledge graph        |
| Relational  | PostgreSQL 16 + SQLAlchemy 2 async + Alembic        |
| Queue       | Redis 7 + Celery (periodic graph maintenance tasks) |
| Auth        | JWT (access + refresh tokens), bcrypt, python-jose  |
| Guardrails  | Prompt injection detection, PII scrubbing (Presidio + regex fallback), length capping |
| Web Search  | DuckDuckGo (no API key required)                    |
| CI/CD       | GitHub Actions (test, build, audit, migration check, MLflow eval) |

## Quick Start

### Prerequisites

    pip install uv
    node --version   # 20+
    docker --version

### Step 1 — Configure environment

    cp backend/.env.example backend/.env
    # Edit backend/.env:
    #   OPENAI_API_KEY=sk-...
    #   SECRET_KEY=$(openssl rand -hex 32)   <-- run this, paste the output

### Step 2 — Start databases (Docker)

    cd backend
    docker-compose up -d postgres neo4j redis
    # Wait ~20s for Neo4j to boot

### Step 3 — Run Alembic migrations

    uv sync
    uv run alembic upgrade head

### Step 4 — Seed Neo4j knowledge graph

    uv run python -m app.db.neo4j_seed

### Step 5 — Start backend

    uv run uvicorn app.main:app --reload --port 8000
    # Verify: curl http://localhost:8000/health

### Step 6 — Start Celery worker + beat (separate terminals)

    uv run celery -A app.tasks.celery_app worker --loglevel=info
    uv run celery -A app.tasks.celery_app beat   --loglevel=info

### Step 7 — Start frontend

    cd frontend
    npm install
    cp .env.example .env.local
    npm run dev
    # Open http://localhost:3000

## API Routes

    GET  /health
    POST /api/v1/auth/register
    POST /api/v1/auth/login
    POST /api/v1/auth/refresh
    GET  /api/v1/auth/me
    POST /api/v1/incident/analyze   (Bearer required)
    GET  /api/v1/stream/incident    (optional Bearer)
    POST /api/v1/chat/              (Bearer required)
    GET  /api/v1/chat/
    GET  /api/v1/chat/{id}
    GET  /api/v1/chat/{id}/messages
    GET  /api/v1/chat/{id}/executions
    DELETE /api/v1/chat/{id}

## Alembic Cheat Sheet

    uv run alembic upgrade head              # apply all migrations
    uv run alembic revision --autogenerate -m "add column"   # create new
    uv run alembic downgrade -1              # rollback one step
    uv run alembic current                   # check DB revision
    uv run alembic check                     # assert no pending changes

## Switching LLM Provider

In backend/.env:

    LLM_PROVIDER=anthropic
    LLM_MODEL=claude-3-5-sonnet-20241022
    ANTHROPIC_API_KEY=sk-ant-...

    LLM_PROVIDER=google
    LLM_MODEL=gemini-1.5-pro
    GOOGLE_API_KEY=AIza...

## Security Guardrails

Every user query passes through app/core/guardrails.py before reaching any LLM:
1. Control character sanitisation
2. Length cap (default 4000 chars)
3. Prompt injection pattern detection
4. PII scrubbing (Presidio or regex fallback)

## Celery Periodic Tasks

| Task                          | Schedule     | Purpose                                  |
|-------------------------------|--------------|------------------------------------------|
| refresh_service_health        | Every 15 min | Update Neo4j service status from web     |
| sync_web_intelligence_to_graph| Every hour   | Write web CVE/bug findings to Neo4j      |
| prune_stale_incidents         | Daily 2 AM   | Remove resolved incidents older than 90d |