# ⚡ Ops-Pilot — AI DevOps Incident Response

AI-powered multi-agent incident response platform. Five specialized agents traverse
your Neo4j service dependency graph, correlate deployments, perform root cause analysis,
and stream remediation plans live to the UI.

## Stack
- **Backend**: Python 3.11, FastAPI, LangGraph, CrewAI, LangChain, Neo4j, PostgreSQL
- **Frontend**: Next.js 14, React, TypeScript, Tailwind, Framer Motion, React Flow, Zustand
- **LLM**: OpenAI-compatible (structured outputs only via `with_structured_output`)

## Quick Start

### Option A — Docker Compose (recommended)
```bash
cp backend/.env.example backend/.env   # fill in OPENAI_API_KEY etc.
docker-compose up --build
docker-compose exec backend uv run python -m app.db.migrations
docker-compose exec backend uv run python -m app.db.neo4j_seed
```

### Option B — Local Dev
See `backend/README.md` and `frontend/README.md`.

## Services
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |
