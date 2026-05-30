<img width="1915" height="919" alt="Opspilot 10" src="https://github.com/user-attachments/assets/aa2242aa-08e8-4c6c-bb8a-bd627740bad4" /># ⚡ Ops-Pilot — AI-Powered SRE Incident Response Platform

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-5-008CC1?style=for-the-badge&logo=neo4j&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6B35?style=for-the-badge&logo=langchain&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-Intelligence-8B5CF6?style=for-the-badge&logo=robot&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22D3EE?style=for-the-badge)
![SSE](https://img.shields.io/badge/Streaming-SSE-00FF88?style=for-the-badge&logo=lightning&logoColor=black)
![CI](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)

Ops-Pilot is a production-grade, multi-agent AI system for SRE incident response. A central orchestrator coordinates twelve specialist AI agents that classify incidents, traverse a service dependency knowledge graph, scan repositories and Terraform state, analyse telemetry, identify root causes, and generate actionable remediation plans — all streamed in real time to the operator via Server-Sent Events.

<img width="1918" height="921" alt="Opspilot 1" src="https://github.com/user-attachments/assets/a13e19cd-2e8f-4b64-8b00-ea41c9cd17a7" />

<img width="1914" height="912" alt="Opspilot 0" src="https://github.com/user-attachments/assets/a07f18cb-3499-4499-942b-5d70b290f8b5" />

---

## Table of Contents

- [Layout][#layout]
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Agent Pipeline](#agent-pipeline)
- [Quick Start](#quick-start)
- [API Routes](#api-routes)
- [Authentication](#authentication)
- [Security Guardrails](#security-guardrails)
- [Streaming (SSE)](#streaming-sse)
- [Neo4j Knowledge Graph](#neo4j-knowledge-graph)
- [LLM Provider Switching](#llm-provider-switching)
- [Alembic Migrations](#alembic-migrations)
- [Celery Periodic Tasks](#celery-periodic-tasks)
- [MCP Integrations](#mcp-integrations)
- [Docker Targets](#docker-targets)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [CI/CD](#cicd)



## Layout

 - <details><summary>Home Page </summary>
     - Dark Mode (Default:
       <img width="1918" height="921" alt="Opspilot 1" src="https://github.com/user-attachments/assets/1765f1e8-2a50-4168-921b-4a3e2843c669" />
     - Light Mode:
<img width="1915" height="917" alt="Opspilot 2" src="https://github.com/user-attachments/assets/9d837dae-72cc-4309-9bf6-69f8dadd69f1" />
      </details>

 - <details><summary>Settings</summary>

  <img width="1919" height="917" alt="Opspilot 3" src="https://github.com/user-attachments/assets/51979de9-449c-400e-b9c2-7e576715fcf2" />
  
 </details>

  - <details><summary>Chat Interface</summary>
<img width="1917" height="915" alt="Opspilot 4" src="https://github.com/user-attachments/assets/cb8d7e47-cac8-40ca-a6f6-9a4b68c24392" />

  <img width="1911" height="918" alt="Flow New" src="https://github.com/user-attachments/assets/fd3d4e0e-2828-41d7-80b6-89197ad70704" />

  <img width="1916" height="910" alt="Explanability" src="https://github.com/user-attachments/assets/97ea5c10-dd48-44cd-bcf5-204dad9126b2" />

<img width="1918" height="903" alt="Cancel" src="https://github.com/user-attachments/assets/7c0863be-931d-43d6-bf69-98d7a82824ac" />

<img width="1921" height="910" alt="Opspilot 9" src="https://github.com/user-attachments/assets/5758e418-46db-4d2e-b937-eef469642091" />

<img width="1915" height="919" alt="Opspilot 10" src="https://github.com/user-attachments/assets/dc6b3fa0-9bda-4ba0-a098-1f697d523cc8" />

 </details>


---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Next.js 15  │  TypeScript  │  Tailwind CSS  │  Framer Motion        │
│  /  /chat  /login  /register  /help  /settings  /contact             │
└──────────────────────────┬───────────────────────────────────────────┘
                           │  SSE + REST  (JWT Bearer)
┌──────────────────────────▼───────────────────────────────────────────┐
│  FastAPI  /api/v1/{auth, incident, chat, stream, health}             │
│  JWT access + refresh tokens  │  bcrypt  │  Guardrails (Presidio)   │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────────────────────┐
│  IncidentOrchestrator  (LangGraph async generator)                   │
│                                                                      │
│   1. Classifier            — severity, service, urgency, type        │
│   2. Entity Extractor      — services, deployments, owners, metrics  │
│   3. Document Processor    — PDF, DOCX, PPTX, CSV, Markdown          │
│   4. Repo Scanner          — GitHub commits, PRs, CI checks          │
│   5. Terraform Scanner     — IaC drift, plans, workspace state       │
│   6. Graph Analyzer        — Neo4j blast-radius + dependency map     │
│   7. Web Intelligence      — DuckDuckGo: CVEs, advisories, outages   │
│   8. Ops Analyst           — latency, error rate, saturation         │
│   9. Crew Intelligence     — CrewAI Researcher→Analyst→Writer        │
│  10. Root Cause Finder     — causal chain + deployment correlation   │
│  11. Remediator            — rollback, runbooks, escalation paths    │
│  12. Conversationalist     — operator-ready Markdown narrative       │
└────────┬──────────────────────┬───────────────────────┬─────────────┘
         │                      │                       │
┌────────▼──────┐  ┌────────────▼──────┐  ┌────────────▼────────────┐
│  Neo4j 5      │  │  PostgreSQL 16    │  │  Redis 7                │
│  Service graph│  │  Users / Chats /  │  │  Celery broker          │
│  knowledge    │  │  Messages /       │  │  + result backend       │
│  base         │  │  Executions       │  │  + periodic tasks       │
└───────────────┘  └───────────────────┘  └─────────────────────────┘
```

---

## Tech Stack

| Layer      | Technology                                                              |
| ---------- | ----------------------------------------------------------------------- |
| Frontend   | Next.js 15, TypeScript, Tailwind CSS, Framer Motion, anime.js, Jest     |
| Backend    | Python 3.11, FastAPI, LangGraph, CrewAI, LangChain                      |
| LLM        | OpenAI (default) · Anthropic · Google — runtime-switchable, no rebuild  |
| Graph DB   | Neo4j 5 — service dependency knowledge graph + blast-radius traversal   |
| Relational | PostgreSQL 16 + SQLAlchemy 2 async + Alembic migrations                 |
| Queue      | Redis 7 + Celery (periodic graph maintenance tasks)                     |
| Auth       | JWT (access + refresh tokens), bcrypt password hashing, python-jose     |
| Guardrails | Prompt injection detection, PII scrubbing (Presidio + regex fallback)   |
| MCP        | GitHub MCP server, Terraform MCP server, custom Ops Inspector server    |
| IaC        | Docker Compose — dev and prod overlays                                  |
| CI/CD      | GitHub Actions — pytest, type-check, lint, migration check, MLflow eval |
| Streaming  | Server-Sent Events (SSE) via sse-starlette                              |

---

## Agent Pipeline

Every incident query travels through the orchestrator's async generator, which yields `StreamEvent` objects that are forwarded directly to the frontend via SSE. Each agent is independently enabled/disabled at runtime by the operator.

### 1. Classifier

Extracts service name, severity (P0–P3), incident type, affected components, trigger event, and confidence score from the raw query using structured LLM output (Pydantic model).

### 2. Entity Extractor

Parses the query for structured entities: service names, deployments, metrics, error codes, time ranges, and Cypher-ready search keywords for downstream graph and web queries.

### 3. Document Processor (optional)

Converts uploaded attachments (PDF, DOCX, PPTX, XLS/XLSX, HTML, Markdown, CSV, TXT) to Markdown and injects them into the pipeline context. All downstream agents receive the full document context.

### 4. Repo Scanner (optional)

Uses the GitHub MCP server to fetch recent commits, open pull requests, failing CI checks, and branch activity for the service repository. Requires `GITHUB_TOKEN`.

### 5. Terraform Scanner (optional)

Uses the Terraform MCP server to inspect workspace state, detect infrastructure drift, and summarise recent plan/apply runs that may correlate with the incident. Requires Terraform MCP configuration.

### 6. Graph Analyzer

Executes nine Cypher queries against the Neo4j knowledge graph: direct dependencies, upstream callers, full blast-radius (3-hop transitive closure), recent deployments, historical incidents, associated runbooks, team ownership, configuration change events, and cross-entity incidents.

### 7. Web Intelligence (optional)

Runs DuckDuckGo searches (Instant Answer API → HTML scrape fallback) for known provider issues, CVEs, post-mortems, and dependency advisories. Results are deduped by URL.

### 8. Ops Analyst (optional)

Uses the custom Ops Inspector MCP server to parse stack traces, calculate error rates, format incident briefs, and check service health from observability tool outputs.

### 9. Crew Intelligence (optional)

Runs a three-role CrewAI crew — Researcher → Analyst → Writer — that gathers, correlates, and synthesises external intelligence into a structured intelligence report injected into the analysis context.

### 10. Root Cause Finder

Synthesises all pipeline context (graph, web, telemetry, repo, IaC) using an LLM to identify the primary root cause, build a causal chain with confidence scores, detect deployment correlation, and reconstruct the incident timeline.

### 11. Remediator

Generates a full remediation plan: immediate kubectl/CLI actions, rollback steps, mitigation steps, escalation paths with Slack contacts, runbook references, and post-incident action items.

### 12. Conversationalist

Synthesises all structured pipeline outputs into a human-readable Markdown narrative including a conversation summary for chat history compaction.

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.11+ with `uv` (install: `pip install uv`)

### 1. Clone and configure

```
git clone https://github.com/your-org/ops-pilot.git
cd ops-pilot
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set at minimum:

- `OPENAI_API_KEY` — your OpenAI key
- `SECRET_KEY` — generate with: `openssl rand -hex 32`

### 2. Start infrastructure

```
cd backend
docker compose up -d postgres neo4j redis
# Allow ~20 s for Neo4j to fully initialise before running migrations
```

### 3. Run migrations and seed the knowledge graph

```
uv sync
uv run alembic upgrade head
uv run python -m app.db.neo4j_seed
```

### 4. Start the API server

```
uv run uvicorn app.main:app --reload --port 8000
# Verify: curl http://localhost:8000/health
```

### 5. Start Celery (two separate terminals)

```
uv run celery -A app.tasks.celery_app worker --loglevel=info
uv run celery -A app.tasks.celery_app beat   --loglevel=info
```

### 6. Start the frontend

```
cd ../frontend
npm install
cp .env.example .env.local
# Set: NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
# Open http://localhost:3000
```

---

## API Routes

```
GET    /health                              Liveness + dependency check

POST   /api/v1/auth/register               Register new user
POST   /api/v1/auth/login                  Login, receive JWT tokens
POST   /api/v1/auth/refresh                Refresh access token
GET    /api/v1/auth/me                     Get current user profile

POST   /api/v1/incident/analyze            Full analysis (Bearer required)
GET    /api/v1/stream/incident             SSE stream (optional Bearer)

POST   /api/v1/chat/                       Create chat session (Bearer)
GET    /api/v1/chat/                       List chat sessions (Bearer)
GET    /api/v1/chat/{id}                   Get chat by ID
GET    /api/v1/chat/{id}/messages          Get messages for chat
GET    /api/v1/chat/{id}/executions        Get agent execution log
DELETE /api/v1/chat/{id}                   Delete chat session

GET    /api/v1/settings                    Get LLM settings (Bearer)
PUT    /api/v1/settings                    Update LLM settings (Bearer)
```

---

## Authentication

Ops-Pilot uses a dual-token JWT strategy:

- **Access token** — short-lived (default 30 min), signed with `SECRET_KEY` using HS256. Sent as `Authorization: Bearer <token>`.
- **Refresh token** — long-lived (default 7 days). Used to obtain a new access token via `POST /api/v1/auth/refresh`.
- Passwords are hashed with **bcrypt** before storage in PostgreSQL.
- The `/api/v1/stream/incident` endpoint accepts an optional Bearer token. Unauthenticated users can still stream results, but their sessions are not persisted to a user account.
- `get_current_user` dependency raises 401 for missing or invalid tokens. `get_optional_user` returns `None` for unauthenticated requests without raising.

---

## Security Guardrails

Every user query (and document context) passes through `app/core/guardrails.py` before reaching any LLM or agent:

1. **Control character sanitisation** — strips null bytes and non-printable characters.
2. **Length enforcement** — caps input at 4,000 characters (`MAX_QUERY_LENGTH`).
3. **Prompt injection detection** — regex pattern matching against known attack phrases such as "ignore all previous instructions", "forget everything", "you are now", "pretend to be", and "act as".
4. **PII scrubbing** — uses Microsoft Presidio (if installed) to redact emails, phone numbers, credit card numbers, IP addresses, and names. Falls back to regex patterns when Presidio is unavailable.

Guardrail violations yield an SSE `error_event` with code `GUARDRAIL_VIOLATION` and terminate the stream immediately. The violation is never forwarded to any LLM.

---

## Streaming (SSE)

The `/api/v1/stream/incident` endpoint opens a Server-Sent Events connection and emits `StreamEvent` objects in real time as the orchestrator progresses through the pipeline.

### Event types

| Event type  | Description                                                          |
| ----------- | -------------------------------------------------------------------- |
| `session`   | Emitted first — contains the `session_id` for this analysis turn     |
| `step`      | Agent lifecycle update (start, complete, error, skipped)             |
| `graph`     | Graph Analyzer result — blast-radius, dependencies, runbooks         |
| `reasoning` | Root Cause Finder result — causal chain, timeline, confidence        |
| `result`    | Final combined output — natural response, structured data, citations |
| `error`     | Stream-level error (guardrail violation, unexpected exception)       |
| `done`      | Stream closed — session_id echoed for confirmation                   |

### StreamEvent schema

Each event's `data` field is a JSON object that always includes:

- `description` — human-readable explanation of what this step does
- `input` — the data this step received
- `output` — the result produced (on complete events)
- `completed_steps` — list of all pipeline steps finished so far
- `error` — error message (on error events only)

### Frontend consumption

The frontend calls `streamIncident()` in `app/lib/apis.ts`, which opens an `EventSource` and dispatches each parsed event to `recordExplainabilityEvent()`. The explainability panel in the chat UI renders each event as a clickable card showing the step name, status, and a hover preview of input/output. Clicking opens a modal with full detail.

---

## Neo4j Knowledge Graph

The graph models the live service dependency topology of your infrastructure. The `GraphAnalyzerAgent` runs nine Cypher queries per incident turn:

1. **Direct dependencies** — services directly called by the affected service
2. **Upstream callers** — services that call into the affected service
3. **Blast radius** — 3-hop transitive closure of all affected nodes
4. **Deployments** — recent deployments across the blast-radius services
5. **Historical incidents** — past incidents on related services
6. **Runbooks** — associated runbook documents with URLs
7. **Ownership** — team ownership records with Slack channels
8. **Config changes** — recent configuration change events
9. **Cross-entity incidents** — incidents touching any extracted entity

### Seeding the knowledge graph

```
uv run python -m app.db.neo4j_seed
```

This creates Service, Deployment, Incident, Runbook, Team, and ConfigChange nodes with realistic relationships for a sample e-commerce microservices topology (checkout, payment, inventory, api-gateway, redis, postgres, etc.).

### Celery graph maintenance

The `sync_web_intelligence_to_graph` Celery task (runs hourly) writes `WebKnowledge` nodes back into Neo4j from web search findings, enabling the graph to accumulate external intelligence over time.

---

## LLM Provider Switching

Edit `backend/.env` — no rebuild required:

```
# OpenAI (default)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# Anthropic Claude
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
LLM_PROVIDER=google
LLM_MODEL=gemini-1.5-pro
GOOGLE_API_KEY=AIza...
```

The LLM provider is resolved at startup in `app/core/llm.py`. All agents use `llm.with_structured_output(PydanticModel)` for type-safe structured outputs.

---

## Alembic Migrations

```
uv run alembic upgrade head                                   apply all pending migrations
uv run alembic revision --autogenerate -m "describe change"   generate a new revision
uv run alembic downgrade -1                                   roll back one step
uv run alembic downgrade <revision_hash>                      roll back to a specific hash
uv run alembic current                                        show current applied revision
uv run alembic check                                          assert no unapplied migrations
uv run alembic history                                        show full migration history
```

Migration files live in `backend/alembic/versions/`. The `alembic.ini` points to the async PostgreSQL DSN from `backend/settings.py`.

---

## Celery Periodic Tasks

| Task                             | Schedule     | Purpose                                          |
| -------------------------------- | ------------ | ------------------------------------------------ |
| `refresh_service_health`         | Every 15 min | Update Neo4j service status from external checks |
| `sync_web_intelligence_to_graph` | Every hour   | Write CVE / advisory findings to Neo4j nodes     |
| `prune_stale_incidents`          | Daily 02:00  | Remove resolved incidents older than 90 days     |

Start with:

```
uv run celery -A app.tasks.celery_app worker --loglevel=info
uv run celery -A app.tasks.celery_app beat   --loglevel=info
```

---

## MCP Integrations

Ops-Pilot connects to external tools via the Model Context Protocol (MCP). Server configuration lives in `backend/mcp_servers/servers.json`.

| Agent             | MCP Server             | Tools exposed                                                                        |
| ----------------- | ---------------------- | ------------------------------------------------------------------------------------ |
| Repo Scanner      | GitHub MCP (official)  | get_repository, list_commits, list_pull_requests, list_check_runs                    |
| Terraform Scanner | Terraform MCP          | workspace_list, plan_show, state_show, apply_status                                  |
| Ops Analyst       | Ops Inspector (custom) | parse_stack_trace, calculate_error_rate, format_incident_brief, check_service_health |

To enable MCP agents, set the required secrets in `servers.json` or via environment variables substituted by `MCPClientManager`:

```
GITHUB_TOKEN=ghp_...        enables Repo Scanner
```

---

## Docker Targets

```
Development (hot reload):
  cd backend && make dev

Production:
  cd backend && make prod

Run migrations via Docker:
  cd backend && make migrate
  cd backend && make migrate-version-up   m=<revision_hash>
  cd backend && make migrate-version-down m=<revision_hash>

Generate a new Alembic revision:
  cd backend && make revision m="add_users_table"

Seed Neo4j:
  cd backend && make seed-neo4j

Clean up Docker:
  cd backend && make prune
```

---

## Environment Variables

| Variable                      | Required | Description                                          |
| ----------------------------- | -------- | ---------------------------------------------------- |
| `SECRET_KEY`                  | Yes      | JWT signing secret — `openssl rand -hex 32`          |
| `OPENAI_API_KEY`              | Yes\*    | Required when `LLM_PROVIDER=openai`                  |
| `ANTHROPIC_API_KEY`           | Yes\*    | Required when `LLM_PROVIDER=anthropic`               |
| `GOOGLE_API_KEY`              | Yes\*    | Required when `LLM_PROVIDER=google`                  |
| `LLM_PROVIDER`                | No       | `openai` (default) / `anthropic` / `google`          |
| `LLM_MODEL`                   | No       | Model name for the selected provider                 |
| `DATABASE_URL`                | No       | PostgreSQL async DSN (defaults to Docker service)    |
| `NEO4J_URI`                   | No       | Neo4j bolt URI (defaults to `bolt://localhost:7687`) |
| `NEO4J_USERNAME`              | No       | Neo4j username (default: `neo4j`)                    |
| `NEO4J_PASSWORD`              | No       | Neo4j password (default: `password`)                 |
| `REDIS_URL`                   | No       | Redis DSN (defaults to `redis://localhost:6379/0`)   |
| `GITHUB_TOKEN`                | No       | GitHub PAT — enables Repo Scanner agent              |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | JWT access token lifetime (default: 30)              |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | No       | JWT refresh token lifetime (default: 7)              |

---

## Testing

```
Backend:
  cd backend
  uv run pytest tests/ -v
  uv run pytest tests/ -v --cov=app --cov-report=term-missing

Frontend:
  cd frontend
  npm test
  npm run test:coverage
```

Test coverage includes: API endpoints, auth flows, all twelve agents (mocked LLM chain), guardrails, orchestrator stream events, and utility functions.

---

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow      | Trigger      | Steps                                            |
| ------------- | ------------ | ------------------------------------------------ |
| `backend-ci`  | Push / PR    | Install deps, run pytest, check Alembic pending  |
| `frontend-ci` | Push / PR    | npm install, Jest, TypeScript type-check, ESLint |
| `lint`        | Push / PR    | Ruff lint, black format check                    |
| `infra`       | Push to main | Docker build validation                          |
| `mlflow`      | Push to main | MLflow evaluation run for LLM output quality     |

---

## License

MIT — see [LICENSE](LICENSE).
