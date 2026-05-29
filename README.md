# ⚡ Ops-Pilot — AI-Powered SRE Incident Response Platform

Ops-Pilot is a production-grade, multi-agent AI platform for SRE incident
response. An orchestrator coordinates twelve specialist agents to classify
incidents, traverse the service dependency graph, scan repositories and
Terraform context, analyse telemetry, determine root cause, and produce
actionable remediation steps — all streamed in real time to the operator.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Next.js 15  │  TypeScript  │  Tailwind  │  Framer Motion        │
│  /  /chat  /login  /register  /help  /settings  /contact         │
└────────────────────────────┬─────────────────────────────────────┘
                             │  SSE + REST  (JWT Bearer)
┌────────────────────────────▼─────────────────────────────────────┐
│  FastAPI  /api/v1/{auth, incident, chat, stream, health}         │
│  JWT (access + refresh)  │  bcrypt  │  Guardrails (Presidio)     │
└────────────────┬─────────────────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────────────────┐
│  IncidentOrchestrator  (LangGraph)                               │
│                                                                  │
│   1. Classifier            — severity, service, urgency          │
│   2. Entity Extractor      — services, owners, deployments       │
│   3. Document Processor    — PDF, DOCX, PPTX, CSV, Markdown      │
│   4. Repo Scanner          — commits, PRs, releases              │
│   5. Terraform Scanner     — workspaces, drift, IaC changes      │
│   6. Graph Analyzer        — Neo4j blast-radius traversal        │
│   7. Ops Analyst           — latency, errors, saturation         │
│   8. Web Intelligence      — provider incidents, CVEs            │
│   9. Crew Intelligence     — CrewAI enrichment synthesis         │
│  10. Root Cause Analyzer   — causal chain, confidence score      │
│  11. Remediator            — rollback, runbook, escalation        │
│  12. Conversationalist     — operator-ready narrative output      │
└────────┬────────────────────────────────────────────────-────────┘
         │
┌────────┴──────────┬────────────────────┬───────────────────────-─┐
│  Neo4j 5          │  PostgreSQL 16      │  Redis 7                │
│  Service graph    │  Users / Chat /     │  Celery broker          │
│  knowledge base   │  Executions         │  + result backend       │
└───────────────────┴─────────────────────┴─────────────────────────┘
```

---

## Tech Stack

| Layer      | Technology                                                          |
| ---------- | ------------------------------------------------------------------- |
| Frontend   | Next.js 15, TypeScript, Tailwind CSS, Framer Motion, anime.js, Jest |
| Backend    | Python 3.11, FastAPI, LangGraph, CrewAI, LangChain                  |
| LLM        | OpenAI (default) · Anthropic · Google — runtime-switchable          |
| Graph DB   | Neo4j 5 — service dependency knowledge graph                        |
| Relational | PostgreSQL 16 + SQLAlchemy 2 async + Alembic                        |
| Queue      | Redis 7 + Celery (periodic maintenance tasks)                       |
| Auth       | JWT (access + refresh tokens), bcrypt, python-jose                  |
| Guardrails | Prompt injection detection, PII scrubbing (Presidio + regex)        |
| IaC        | Docker Compose (dev + prod overlays)                                |
| CI/CD      | GitHub Actions — test, build, audit, migration check, MLflow eval   |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.11+ with `uv` (`pip install uv`)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/ops-pilot.git
cd ops-pilot

cp backend/.env.example backend/.env
# Required: set OPENAI_API_KEY and SECRET_KEY
# Generate SECRET_KEY:  openssl rand -hex 32
```

### 2. Start databases

```bash
cd backend
docker compose up -d postgres neo4j redis
# Allow ~20s for Neo4j to fully initialise
```

### 3. Run migrations and seed

```bash
uv sync
uv run alembic upgrade head
uv run python -m app.db.neo4j_seed
```

### 4. Start the backend

```bash
uv run uvicorn app.main:app --reload --port 8000
# Health check: curl http://localhost:8000/health
```

### 5. Start Celery (two separate terminals)

```bash
uv run celery -A app.tasks.celery_app worker --loglevel=info
uv run celery -A app.tasks.celery_app beat   --loglevel=info
```

### 6. Start the frontend

```bash
cd ../frontend
npm install
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
# Open http://localhost:3000
```

---

## API Routes

```
GET    /health
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me
POST   /api/v1/incident/analyze       # Bearer required
GET    /api/v1/stream/incident        # optional Bearer
POST   /api/v1/chat/                  # Bearer required
GET    /api/v1/chat/
GET    /api/v1/chat/{id}
GET    /api/v1/chat/{id}/messages
GET    /api/v1/chat/{id}/executions
DELETE /api/v1/chat/{id}
```

---

## Alembic Migrations

```bash
uv run alembic upgrade head                                  # apply all
uv run alembic revision --autogenerate -m "describe change"  # new revision
uv run alembic downgrade -1                                  # roll back one
uv run alembic downgrade <revision_hash>                     # roll back to hash
uv run alembic current                                       # current revision
uv run alembic check                                         # assert no pending
```

---

## Switching LLM Provider

Edit `backend/.env`:

```bash
# OpenAI (default)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Google
LLM_PROVIDER=google
LLM_MODEL=gemini-1.5-pro
GOOGLE_API_KEY=AIza...
```

No backend rebuild required — settings are applied at runtime.

---

## Security Guardrails

Every user query passes through `app/core/guardrails.py` before reaching any LLM:

1. Control character sanitisation
2. Length cap (default 4 000 characters)
3. Prompt injection pattern detection
4. PII scrubbing (Microsoft Presidio when installed, regex fallback)

---

## Celery Periodic Tasks

| Task                             | Schedule     | Purpose                                   |
| -------------------------------- | ------------ | ----------------------------------------- |
| `refresh_service_health`         | Every 15 min | Update Neo4j service status from web      |
| `sync_web_intelligence_to_graph` | Every hour   | Write CVE / advisory findings to Neo4j    |
| `prune_stale_incidents`          | Daily 02:00  | Remove resolved incidents older than 90 d |

---

## Docker Targets

```bash
# Development (hot reload)
cd backend && make dev

# Production
cd backend && make prod

# Migrations via Docker
cd backend && make migrate
cd backend && make migrate-version-up   m=<revision_hash>
cd backend && make migrate-version-down m=<revision_hash>

# Generate a new revision
cd backend && make revision m="add_users_table"

# Seed Neo4j
cd backend && make seed-neo4j
```

---

## License

MIT — see [LICENSE](LICENSE).
