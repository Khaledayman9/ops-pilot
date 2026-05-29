# Ops-Pilot — Backend

FastAPI · LangGraph · CrewAI · Neo4j · PostgreSQL · Redis · Celery

---

## Setup (Local Development)

### 1. Install dependencies

```bash
pip install uv
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# Required fields:
#   OPENAI_API_KEY=sk-...
#   SECRET_KEY=$(openssl rand -hex 32)
```

### 3. Start databases

```bash
docker compose up -d postgres neo4j redis
# Neo4j needs ~20 s to fully boot before running migrations
```

### 4. Run migrations

```bash
uv run alembic upgrade head
```

### 5. Seed Neo4j knowledge graph

```bash
uv run python -m app.db.neo4j_seed
```

### 6. Start the API server

```bash
uv run uvicorn app.main:app --reload --port 8000
# Verify: curl http://localhost:8000/health
```

### 7. Start Celery (two separate terminals)

```bash
uv run celery -A app.tasks.celery_app worker --loglevel=info
uv run celery -A app.tasks.celery_app beat   --loglevel=info
```

### 8. Run tests

```bash
uv run pytest tests/ -v
```

---

## Makefile Targets

```bash
make dev                              # docker compose up --build (dev overlay)
make up                               # docker compose up
make down                             # docker compose down
make prod                             # pull + up (prod overlay)
make migrate                          # alembic upgrade head
make migrate-version-up   m=<hash>    # alembic upgrade <hash>
make migrate-version-down m=<hash>    # alembic downgrade <hash>
make revision             m="label"   # alembic revision --autogenerate
make seed-neo4j                       # python -m app.db.neo4j_seed
make prune                            # docker system prune
```

---

## Alembic Migrations

```bash
uv run alembic upgrade head                                   # apply all pending
uv run alembic revision --autogenerate -m "describe change"   # generate revision
uv run alembic downgrade -1                                   # roll back one step
uv run alembic downgrade <revision_hash>                      # roll back to hash
uv run alembic current                                        # current revision
uv run alembic check                                          # assert no pending
```

> Use `alembic downgrade`, not `alembic down` — `down` is not a valid subcommand.

---

## Agent Pipeline

```
Orchestrator
 ├── Classifier              — severity, service, incident type, urgency
 ├── Entity Extractor        — services, owners, deployments, timestamps
 ├── Document Processor      — PDF, DOCX, PPTX, HTML, Excel, CSV, Markdown
 ├── Repo Scanner            — commits, PRs, releases, deployment metadata
 ├── Terraform Scanner       — workspaces, drift, plans, IaC state signals
 ├── Graph Analyzer          — Neo4j dependency + blast-radius traversal
 ├── Ops Analyst             — latency, error rate, saturation, CPU/memory
 ├── Web Intelligence        — provider incidents, CVEs, dependency advisories
 ├── Crew Intelligence       — CrewAI enrichment synthesis
 ├── Root Cause Analyzer     — causal chain with evidence confidence score
 ├── Remediator              — rollback, mitigation, escalation, runbook links
 └── Conversationalist       — operator-ready narrative response
```

All agents extend `BaseAgent` (`app/core/base_agent.py`).
All LLM calls use `llm.with_structured_output(PydanticModel)`.

---

## LLM Provider Selection

```bash
# backend/.env

LLM_PROVIDER=openai        # default
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

LLM_PROVIDER=google
LLM_MODEL=gemini-1.5-pro
GOOGLE_API_KEY=AIza...
```

No rebuild required — provider is resolved at startup via `app/core/llm_factory.py`.

---

## Security Guardrails

All user input passes through `app/core/guardrails.py` before any LLM call:

- Sanitise control characters
- Enforce length cap (`MAX_QUERY_LENGTH`, default 4 000)
- Detect prompt injection patterns
- Scrub PII (Microsoft Presidio when installed, regex fallback)

---

## API Structure

```
app/api/__init__.py          aggregated router
app/api/uris.py              URI constants (no magic strings)
app/api/dtos.py              re-exported schema DTOs
app/api/deps.py              get_current_user, get_optional_user
app/api/routes/
    auth.py                  /api/v1/auth/*
    incident.py              /api/v1/incident/*
    chat.py                  /api/v1/chat/*
    stream.py                /api/v1/stream/*
    health.py                /health
```

---

## Neo4j Knowledge Graph

The `GraphAnalyzerAgent` runs nine Cypher queries per incident:

1. Direct service dependencies
2. Upstream callers
3. Full blast radius (3-hop transitive closure)
4. Deployments across blast-radius services
5. Historical incidents
6. Associated runbooks
7. Team ownership
8. Configuration change events
9. Cross-entity incidents

`WebKnowledge` nodes are written back to Neo4j by the Celery
`sync_web_intelligence_to_graph` task every hour.

---

## Celery Periodic Tasks

| Task                             | Schedule     | Purpose                                 |
| -------------------------------- | ------------ | --------------------------------------- |
| `refresh_service_health`         | Every 15 min | Update Neo4j service status             |
| `sync_web_intelligence_to_graph` | Every hour   | Write CVE/advisory findings to Neo4j    |
| `prune_stale_incidents`          | Daily 02:00  | Remove incidents resolved > 90 days ago |

---

## Environment Variables Reference

| Variable            | Required | Description                                 |
| ------------------- | -------- | ------------------------------------------- |
| `SECRET_KEY`        | Yes      | JWT signing secret (`openssl rand -hex 32`) |
| `OPENAI_API_KEY`    | Yes\*    | Required if `LLM_PROVIDER=openai`           |
| `ANTHROPIC_API_KEY` | Yes\*    | Required if `LLM_PROVIDER=anthropic`        |
| `GOOGLE_API_KEY`    | Yes\*    | Required if `LLM_PROVIDER=google`           |
| `LLM_PROVIDER`      | No       | `openai` (default) / `anthropic` / `google` |
| `LLM_MODEL`         | No       | Model name for selected provider            |
| `DATABASE_URL`      | No       | PostgreSQL DSN (defaults to Docker service) |
| `NEO4J_URI`         | No       | Neo4j bolt URI (defaults to Docker service) |
| `REDIS_URL`         | No       | Redis DSN (defaults to Docker service)      |
