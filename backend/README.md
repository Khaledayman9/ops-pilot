# Ops-Pilot — Backend

FastAPI · LangGraph · CrewAI · LangChain · Neo4j · PostgreSQL · Redis · Celery · MCP

---

## Table of Contents

- [Setup (Local Development)](#setup-local-development)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Agent Pipeline — Deep Dive](#agent-pipeline--deep-dive)
- [Orchestrator and Streaming](#orchestrator-and-streaming)
- [BaseAgent Contract](#baseagent-contract)
- [Neo4j Knowledge Graph](#neo4j-knowledge-graph)
- [Authentication and Authorization](#authentication-and-authorization)
- [Security Guardrails](#security-guardrails)
- [MCP Integrations](#mcp-integrations)
- [LLM Provider Selection](#llm-provider-selection)
- [API Structure](#api-structure)
- [Alembic Migrations](#alembic-migrations)
- [Celery Periodic Tasks](#celery-periodic-tasks)
- [Makefile Targets](#makefile-targets)
- [Testing](#testing)

---

## Setup (Local Development)

### 1. Install Python dependencies

```
pip install uv
uv sync
```

### 2. Configure environment

```
cp .env.example .env
```

Minimum required fields in `.env`:

```
OPENAI_API_KEY=sk-...
SECRET_KEY=<output of: openssl rand -hex 32>
```

### 3. Start infrastructure

```
docker compose up -d postgres neo4j redis
```

Neo4j needs approximately 20 seconds to fully boot before migrations can run.

### 4. Run database migrations

```
uv run alembic upgrade head
```

### 5. Seed the Neo4j knowledge graph

```
uv run python -m app.db.neo4j_seed
```

This creates a full sample service dependency topology including Service, Deployment, Incident, Runbook, Team, and ConfigChange nodes with realistic relationships for a microservices e-commerce stack.

### 6. Start the API server

```
uv run uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health`

### 7. Start Celery workers (two separate terminals)

```
uv run celery -A app.tasks.celery_app worker --loglevel=info
uv run celery -A app.tasks.celery_app beat   --loglevel=info
```

### 8. Run tests

```
uv run pytest tests/ -v
```

---

## Environment Variables

| Variable                      | Required | Default              | Description                                    |
| ----------------------------- | -------- | -------------------- | ---------------------------------------------- |
| `SECRET_KEY`                  | Yes      | —                    | JWT signing secret (`openssl rand -hex 32`)    |
| `OPENAI_API_KEY`              | Yes\*    | —                    | Required when `LLM_PROVIDER=openai`            |
| `ANTHROPIC_API_KEY`           | Yes\*    | —                    | Required when `LLM_PROVIDER=anthropic`         |
| `GOOGLE_API_KEY`              | Yes\*    | —                    | Required when `LLM_PROVIDER=google`            |
| `LLM_PROVIDER`                | No       | `openai`             | LLM backend: `openai` / `anthropic` / `google` |
| `LLM_MODEL`                   | No       | `gpt-4o`             | Model name for the selected provider           |
| `DATABASE_URL`                | No       | Docker postgres DSN  | PostgreSQL async connection string             |
| `NEO4J_URI`                   | No       | `bolt://neo4j:7687`  | Neo4j bolt connection URI                      |
| `NEO4J_USERNAME`              | No       | `neo4j`              | Neo4j username                                 |
| `NEO4J_PASSWORD`              | No       | `password`           | Neo4j password                                 |
| `REDIS_URL`                   | No       | `redis://redis:6379` | Redis connection string                        |
| `GITHUB_TOKEN`                | No       | —                    | GitHub PAT — enables Repo Scanner agent        |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | `30`                 | JWT access token lifetime in minutes           |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | No       | `7`                  | JWT refresh token lifetime in days             |

---

## Project Structure

```
backend/
  app/
    agents/
      classifier/           LLM classification: service, severity, type, confidence
      entity_extractor/     Structured entity parsing: services, metrics, error codes
      conversationalist/    Natural language narrative synthesis for every turn
      document_processor/   File-to-Markdown conversion for uploaded attachments
      graph_analyzer/       Neo4j Cypher traversal for blast radius and topology
      ops_analyst/          Telemetry analysis via Ops Inspector MCP server
      orchestrator/         LangGraph async generator coordinating all agents
        graph.py            IncidentOrchestrator.run_with_stream() — main pipeline
        models.py           IncidentState — mutable shared state across agents
        utils.py            Context builders and history compaction utilities
      remediator/           Remediation plan: actions, rollback, escalation, runbooks
      repo_scouter/         GitHub MCP integration for code change analysis
      root_cause_finder/    Causal chain analysis with confidence scoring
      terraform_scouter/    Terraform/IaC MCP integration for drift detection
      web_searcher/         DuckDuckGo web search for CVEs and post-mortems
      crew/                 CrewAI multi-agent intelligence crew
    api/
      routes/
        auth.py             POST /register, POST /login, POST /refresh, GET /me
        incident.py         POST /analyze (full synchronous analysis)
        chat.py             CRUD for chat sessions and message history
        stream.py           GET /stream/incident (SSE streaming endpoint)
        health.py           GET /health
      deps.py               FastAPI dependencies: get_current_user, get_optional_user
      dtos.py               Re-exported Pydantic schemas for API boundary
      uris.py               URI constants (no magic strings in route files)
    core/
      base_agent.py         BaseAgent abstract class all agents extend
      guardrails.py         Input sanitisation, injection detection, PII scrubbing
      llm.py                LLM factory — resolves provider and model at startup
      security.py           JWT encode/decode, bcrypt hashing, token verification
      utils.py              Shared utility functions
    db/
      models.py             SQLAlchemy ORM models: User, Chat, Message, AgentExecution
      postgres.py           Async session factory and get_db dependency
      neo4j.py              Neo4j driver singleton and session context manager
      neo4j_seed.py         Knowledge graph seed script
      migrations.py         Migration utilities
    schemas/
      auth.py               UserCreate, UserPublic, TokenResponse, LoginRequest
      chat.py               ChatCreate, MessageCreate, ChatResponse
      stream.py             StreamEvent — the SSE event envelope
      incident.py           IncidentResponse for synchronous analysis route
    services/
      auth_service.py       Registration, login, token refresh, user lookup
      chat_service.py       Chat CRUD, message storage, agent execution logging
      incident_service.py   Synchronous analysis wrapper around the orchestrator
      neo4j_service.py      Neo4j helper queries for the API layer
    tasks/
      celery_app.py         Celery application and beat schedule
      graph_maintenance.py  Periodic tasks: health refresh, web sync, incident prune
    main.py                 FastAPI app factory, router registration, lifespan

  mcp_servers/
    servers.json            MCP server configuration (GitHub, Terraform, Ops Inspector)
    mcp_client_manager.py   Async MCP client lifecycle manager
    servers/
      ops_inspector.py      Custom MCP server implementing ops diagnostic tools

  alembic/
    versions/               Migration revision files
    env.py                  Alembic environment with async SQLAlchemy support

  tests/
    conftest.py             Shared pytest fixtures for all agent tests
    test_api.py             API endpoint integration tests
    test_auth.py            Auth flow tests (register, login, tokens)
    test_classifier.py      ClassifierAgent unit tests
    test_entity_extractor.py EntityExtractorAgent unit tests
    test_graph_agent.py     GraphAnalyzerAgent unit tests
    test_guardrails.py      Guardrail unit tests
    test_orchestrator.py    Full orchestrator stream tests
    test_conversationalist.py ConversationalistAgent unit tests
    test_root_cause_finder.py RootCauseFinderAgent unit tests
    test_remediator.py      RemediatorAgent unit tests
    test_web_searcher.py    WebSearcherAgent unit tests
    test_repo_scouter.py    RepoScoutAgent unit tests
    test_terraform_scouter.py TerraformScoutAgent unit tests
    test_ops_analyst.py     OpsAnalystAgent unit tests
```

---

## Agent Pipeline — Deep Dive

### Classifier

Input: raw incident query string.
Output: `ClassificationOutput` — service name, severity (P0–P3), incident_type (latency / error_rate / outage / memory / cpu / disk / network / unknown), affected_components list, trigger_event, confidence score (0.0–1.0).

If confidence is below 0.25 or service resolves to "none"/"unknown", the orchestrator routes directly to the Conversationalist for a general chat response, bypassing the full incident pipeline.

### Entity Extractor

Input: query + service name + incident type.
Output: `EntityExtractorOutput` — structured `EntityExtraction` (services, deployments, metrics, error_codes, time_range, keywords) + `search_queries` list (Cypher-ready) + `context_summary`.

The `search_queries` are used directly by the Graph Analyzer for targeted Cypher lookups.

### Document Processor

Converts uploaded files using `markitdown` and `pypandoc`. Supported formats: PDF, DOCX, PPTX, XLS/XLSX, HTML, Markdown, CSV, TXT. The resulting Markdown is injected into `IncidentState.document_context` and prepended to the effective query sent to all downstream agents.

### Graph Analyzer

Runs nine Cypher queries against the Neo4j knowledge graph. Falls back to mock data if Neo4j is unreachable (for development without a running Neo4j instance).

Output: `GraphAnalyzerQueryOutput` — upstream_services, downstream_services, blast_radius_count, recent_deployments, related_incidents, runbooks, ownership, graph_summary, dependency_edges.

### Root Cause Finder

Takes the full pipeline context: query, service, severity, incident_type, graph_context (all nine query results), classification dict, and optional web_context string.

Output: `RootCauseFinderOutput` — primary_cause, causal_chain (list of `CausalFactor` with factor + confidence + evidence), contributing_factors, deployment_correlation bool, deployment_version, timeline_reconstruction list, confidence_score, reasoning.

### Remediator

Takes: service, severity, primary_cause, causal_chain, blast_radius dict, deployment_correlation, deployment_version.

Output: `RemediatorOutput` — immediate_actions, rollback_steps, mitigation_steps (all `RemediationStep` with order, action, command, expected_outcome, risk_level, estimated_minutes), escalation_paths (team, contact, condition), runbook_references, estimated_resolution_minutes, post_incident_actions, summary.

### Conversationalist

Runs on every turn — both incident-relevant and general queries.

For incident queries: synthesises root_cause, remediation_steps, rollback_steps, timeline, blast_radius, causal_chain, and web_citations into a Markdown narrative with a concise summary (≤120 words) for history compaction.

For off-topic queries: generates a helpful direct response without fabricating incident analysis, setting `is_incident_relevant=False`.

---

## Orchestrator and Streaming

`IncidentOrchestrator.run_with_stream()` is an async generator that yields `StreamEvent` objects. The SSE endpoint in `stream.py` iterates the generator and emits each event as `data: <json>\n\n`.

Each `StreamEvent` carries:

- `event` — event type: step / graph / reasoning / result / error / done
- `agent` — agent key (e.g. "classifier", "graph_analyzer")
- `step` — step name within the agent (e.g. "classify", "graph_traversal")
- `status` — running / complete / error / skipped
- `data` — dict containing: description, input, output, completed_steps, and agent-specific fields

The `IncidentState` dataclass is the shared mutable context passed between agents within a single orchestrator turn. It accumulates outputs from each agent and is used to build the final `result` event.

---

## BaseAgent Contract

All agents extend `BaseAgent` in `app/core/base_agent.py`. The base class:

- Loads YAML prompt files from `<agent>/prompts.yaml` (keys: `system`, `user_template`)
- Initialises the LLM via `app/core/llm.py`
- Provides `_build_chain(OutputModel)` which returns `llm.with_structured_output(OutputModel)`
- Provides `_log(message, level)` for structured logging
- Exposes `self.llm` and `self.agent_name`
- Exposes `self._prompts` dict with loaded YAML content

MCP-backed agents (RepoScout, TerraformScout, OpsAnalyst) also hold an `asyncio.Lock` for one-time async initialisation and a `_tool_names` list populated after MCP connection.

---

## Neo4j Knowledge Graph

### Node types

| Label        | Key properties                                 |
| ------------ | ---------------------------------------------- |
| Service      | name, status, language, version, team          |
| Deployment   | version, status, timestamp, service_name       |
| Incident     | id, severity, status, description, timestamp   |
| Runbook      | id, title, url, applies_to                     |
| Team         | name, slack_channel, pagerduty_schedule        |
| ConfigChange | id, type, description, timestamp, service_name |
| WebKnowledge | title, url, snippet, topic, created_at         |

### Relationship types

```
(Service)-[:DEPENDS_ON]->(Service)
(Service)-[:OWNED_BY]->(Team)
(Deployment)-[:DEPLOYED_TO]->(Service)
(Incident)-[:AFFECTS]->(Service)
(Runbook)-[:APPLIES_TO]->(Service)
(ConfigChange)-[:CHANGED]->(Service)
(WebKnowledge)-[:RELATES_TO]->(Service)
```

### Cypher queries executed per incident

1. `MATCH (s:Service {name: $service})-[:DEPENDS_ON]->(dep)` — direct dependencies
2. `MATCH (caller)-[:DEPENDS_ON]->(s:Service {name: $service})` — upstream callers
3. `MATCH (s:Service {name: $service})-[:DEPENDS_ON*1..3]->(b)` — blast radius (3-hop)
4. `MATCH (d:Deployment)-[:DEPLOYED_TO]->(b)` — deployments in blast radius
5. `MATCH (i:Incident)-[:AFFECTS]->(b)` — historical incidents
6. `MATCH (r:Runbook)-[:APPLIES_TO]->(b)` — runbooks
7. `MATCH (t:Team)-[:OWNED_BY]-(b)` — team ownership
8. `MATCH (c:ConfigChange)-[:CHANGED]->(b)` — config changes
9. `MATCH (i:Incident)-[:AFFECTS]->(e)` WHERE e.name IN $entities — cross-entity incidents

---

## Authentication and Authorization

The auth system lives in `app/services/auth_service.py` and `app/core/security.py`.

### Registration flow

1. Validate email uniqueness and username uniqueness in PostgreSQL.
2. Hash password with bcrypt (`passlib[bcrypt]`).
3. Create `User` record with `is_active=True`, `is_verified=False`.
4. Return `UserPublic` schema (never the hashed password).

### Login flow

1. Look up user by email.
2. Verify bcrypt hash.
3. Generate access token (JWT, HS256, `ACCESS_TOKEN_EXPIRE_MINUTES` TTL).
4. Generate refresh token (JWT, HS256, `REFRESH_TOKEN_EXPIRE_DAYS` TTL).
5. Return `TokenResponse` with both tokens.

### Token refresh flow

1. Decode and validate the refresh token.
2. Look up user by ID from token `sub` claim.
3. Issue a new access token.

### FastAPI dependencies

- `get_current_user` — decodes Bearer token, raises 401 on failure. Used on all protected routes.
- `get_optional_user` — same but returns `None` instead of raising. Used on the SSE stream endpoint.

---

## Security Guardrails

All user input (query + document_context) passes through `app/core/guardrails.py` before reaching any LLM:

### apply_all(text) pipeline

1. `sanitise_input(text)` — strips null bytes and control characters
2. `enforce_length(text)` — truncates to `MAX_QUERY_LENGTH` (4000 chars)
3. `check_prompt_injection(text)` — raises `GuardrailViolation` if injection patterns matched
4. `scrub_pii(text)` — redacts PII using Presidio or regex fallback

### Injection patterns detected

The regex set covers: "ignore all previous instructions", "forget everything", "you are now", "pretend to be", "act as", "jailbreak", "bypass", "reveal your prompt", "system prompt", and similar known attack phrases.

### PII scrubbing

When `microsoft-presidio` is installed: uses NLP entity recognition for PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IP_ADDRESS, US_SSN, and more.

Regex fallback: matches email addresses (`[\w.-]+@[\w.-]+`) and IPv4 addresses (`\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`).

---

## MCP Integrations

MCP (Model Context Protocol) allows agents to call external tools through a standardised protocol. The `MCPClientManager` in `mcp_servers/mcp_client_manager.py` manages async MCP client lifecycles.

### servers.json structure

```
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_TOKEN": "${GITHUB_TOKEN}"
    }
  },
  "terraform": {
    "command": "...",
    "args": [...]
  },
  "ops-inspector": {
    "command": "python",
    "args": ["-m", "mcp_servers.servers.ops_inspector"]
  }
}
```

Environment variable substitution (`${VAR}`) is handled by `MCPClientManager` at connection time.

### Ops Inspector MCP Server

A custom MCP server (`mcp_servers/servers/ops_inspector.py`) that exposes four tools to the `OpsAnalystAgent`:

| Tool                    | Description                                                |
| ----------------------- | ---------------------------------------------------------- |
| `parse_stack_trace`     | Identifies exception type, root frame, and likely cause    |
| `calculate_error_rate`  | Computes error rate, labels severity, checks SLO threshold |
| `format_incident_brief` | Structures incident data into a standardised brief format  |
| `check_service_health`  | Evaluates service health from provided metric signals      |

---

## LLM Provider Selection

The LLM is initialised once at startup in `app/core/llm.py` and shared across all agents.

```
LLM_PROVIDER=openai       → ChatOpenAI(model=LLM_MODEL)
LLM_PROVIDER=anthropic    → ChatAnthropic(model=LLM_MODEL)
LLM_PROVIDER=google       → ChatGoogleGenerativeAI(model=LLM_MODEL)
```

All agents use `self.llm.with_structured_output(PydanticModel)` which instructs the LLM to return JSON conforming to the Pydantic schema. This eliminates manual JSON parsing and provides full type safety.

---

## API Structure

```
app/api/__init__.py          Aggregated router — includes all sub-routers
app/api/uris.py              URI constant classes (AuthURIs, IncidentURIs, etc.)
app/api/dtos.py              Re-exported schema DTOs for API consumers
app/api/deps.py              get_current_user, get_optional_user dependencies
app/api/routes/
    auth.py                  /api/v1/auth/register, /login, /refresh, /me
    incident.py              /api/v1/incident/analyze (synchronous)
    chat.py                  /api/v1/chat/ CRUD + messages + executions
    stream.py                /api/v1/stream/incident (SSE)
    health.py                /health (liveness + DB connectivity)
    settings.py              /api/v1/settings (LLM config per user)
```

---

## Alembic Migrations

Migration files live in `alembic/versions/`. The Alembic environment is configured for async SQLAlchemy in `alembic/env.py`.

```
uv run alembic upgrade head                                    apply all pending
uv run alembic revision --autogenerate -m "describe change"    create new revision
uv run alembic downgrade -1                                    roll back one step
uv run alembic downgrade <revision_hash>                       roll back to hash
uv run alembic current                                         show current revision
uv run alembic check                                           assert no pending
uv run alembic history                                         show full history
```

Use `alembic downgrade`, not `alembic down` — `down` is not a valid subcommand.

Existing revisions:

- `c36997241853` — init (User, Chat, Message tables)
- `17277c625055` — v2 (AgentExecution table)
- `26f645063c9a` — v3 (settings and refresh token fields)

---

## Celery Periodic Tasks

Defined in `app/tasks/graph_maintenance.py`, scheduled in `app/tasks/celery_app.py`.

| Task                             | Schedule     | Description                                                |
| -------------------------------- | ------------ | ---------------------------------------------------------- |
| `refresh_service_health`         | Every 15 min | Fetches service health signals and updates Neo4j nodes     |
| `sync_web_intelligence_to_graph` | Every hour   | Writes CVE / advisory / web findings as WebKnowledge nodes |
| `prune_stale_incidents`          | Daily 02:00  | Deletes resolved Incident nodes older than 90 days         |

The Celery broker and result backend both use Redis (`REDIS_URL`).

---

## Makefile Targets

```
make dev                               docker compose up --build (dev overlay)
make up                                docker compose up
make down                              docker compose down
make prod                              docker compose pull + up (prod overlay)
make migrate                           alembic upgrade head
make migrate-version-up   m=<hash>     alembic upgrade <hash>
make migrate-version-down m=<hash>     alembic downgrade <hash>
make revision             m="label"    alembic revision --autogenerate -m "label"
make seed-neo4j                        python -m app.db.neo4j_seed
make prune                             docker system prune -f
```

---

## Testing

Tests use `pytest` with `pytest-asyncio`. The `conftest.py` defines shared Pydantic fixtures for all agent outputs.

```
uv run pytest tests/ -v
uv run pytest tests/ -v --cov=app --cov-report=term-missing
uv run pytest tests/test_classifier.py -v           run a single file
uv run pytest tests/ -k "test_guardrail" -v         run matching tests
```

### Test coverage by file

| Test file                   | What it tests                                                        |
| --------------------------- | -------------------------------------------------------------------- |
| `test_api.py`               | Health, auth-required routes, mock-auth analysis, SSE guardrail      |
| `test_auth.py`              | Register, login, health endpoints via mocked AuthService             |
| `test_classifier.py`        | ClassifierAgent output schema, BaseAgent inheritance, prompts        |
| `test_entity_extractor.py`  | EntityExtractorAgent search query generation, BaseAgent              |
| `test_graph_agent.py`       | GraphAnalyzerAgent output, Neo4j mock, runbook/ownership queries     |
| `test_guardrails.py`        | Length cap, null byte sanitise, injection patterns, PII scrub        |
| `test_orchestrator.py`      | Full stream events, all-agent-error resilience                       |
| `test_conversationalist.py` | Incident + off-topic responses, history handling, schema             |
| `test_root_cause_finder.py` | Causal chain, deployment correlation, timeline, empty graph          |
| `test_remediator.py`        | Actions, escalation, runbooks, P0 severity, no-deployment            |
| `test_web_searcher.py`      | Output schema, deduplication, deployment query, empty results, utils |
| `test_repo_scouter.py`      | MCP output, timeout handling, init failure, input schema             |
| `test_terraform_scouter.py` | Output, timeout, config missing, response fallback                   |
| `test_ops_analyst.py`       | All AnalysisTask variants, timeout, MCP failure, schema              |
