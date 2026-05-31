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

The pipeline is an async generator (`IncidentOrchestrator.run_with_stream`) that executes agents in sequence, yielding `StreamEvent` objects consumed by the SSE endpoint. Agents share mutable `IncidentState`. Non-fatal agent failures are logged and the pipeline continues; fatal failures (classifier, graph_analyzer) may degrade output quality but never crash the stream.

### Document Processor

**Enabled:** Only when `document_processor` is in `enabled_agents` (the SSE endpoint adds it automatically when `document_context` is non-empty — i.e. the user uploaded a file).

**Input:** Uploaded file path, filename, optional MIME type.
**Output:** `DocumentProcessorOutput` — markdown string, character count, chunk count.

Uses `markitdown` for conversion. Supports PDF, DOCX, PPTX, XLS/XLSX, HTML, Markdown, CSV, TXT. The resulting Markdown is injected into `IncidentState.document_context` by the SSE layer before the orchestrator starts. The Document Processor step in the pipeline emits `running` then `complete` (or `error`) events so the frontend can display it in the explainability sidebar.

If `document_processor` is not in `enabled_agents`, the step emits `skipped` and the pipeline proceeds without document context.

### Classifier

**Input:** Raw incident query string (with document context prepended if present).
**Output:** `ClassificationOutput` — service name, severity (P0–P3), incident_type (latency / error_rate / outage / memory / cpu / disk / network / unknown), affected_components list, trigger_event, confidence score (0.0–1.0).

If confidence is below 0.25 or service resolves to "none" / "unknown", the orchestrator routes directly to the Conversationalist for a general chat response, bypassing the full incident pipeline.

Every StreamEvent for this step includes `input` (the first 300 chars of the effective query) and `output` (service / severity / type summary on complete, or the raw error string in `error` on failure).

### Entity Extractor

**Input:** Query + service name + incident type.
**Output:** `EntityExtractorOutput` — structured `EntityExtraction` (services, deployments, metrics, error_codes, time_range, keywords) + `search_queries` list (Cypher-ready) + `context_summary`.

The `search_queries` are used directly by the Graph Analyzer for targeted Cypher lookups. The `context_summary` is passed to downstream agents for enriched prompting.

### Repo Scout (optional)

**Enabled by default.** Disabled if user removes `repo_scout` from enabled_agents.
**Requires:** `GITHUB_TOKEN` environment variable. Without it, MCP connection fails and the step emits `error` but the pipeline continues.

**Input:** `owner/repo` derived from the service name, task type, extra context.
**Output:** `RepoScoutOutput` — summary string, tools_used list.

Uses the `@modelcontextprotocol/server-github` MCP server to fetch recent commits, open PRs, and failing CI checks. Results are appended to `web_context` passed to downstream agents.

### Terraform Scout (optional)

**Enabled by default.** Disabled if user removes `terraform_scout` from enabled_agents.

**Input:** Terraform workspace name (derived from service), task type, extra context.
**Output:** `TerraformScoutOutput` — summary string, tools_used list.

Uses a Terraform MCP server to inspect workspace state for recent plan/apply runs and infrastructure drift. Results are appended to `web_context`.

### Graph Analyzer

**Required.** Always runs for incident queries.

Runs nine Cypher queries against the Neo4j knowledge graph. Falls back gracefully if Neo4j is unreachable (development mode returns mock topology data so the pipeline still completes).

**Output:** `GraphAnalyzerQueryOutput`:

- `upstream_services` — services that call the affected service
- `downstream_services` — services the affected service calls
- `blast_radius_count` — total nodes in 3-hop dependency radius
- `recent_deployments` — deployments in the blast radius in the last 24h
- `related_incidents` — historical incidents affecting blast radius services
- `runbooks` — runbook references for affected services
- `ownership` — owning team names and Slack channels
- `graph_summary` — human-readable topology summary
- `dependency_edges` — list of `[source, target]` pairs for visualisation

The nine Cypher queries are documented in the Neo4j Knowledge Graph section below.

### Web Searcher (optional)

**Enabled by default.** Disabled if user removes `web_searcher` from enabled_agents.

Runs DuckDuckGo searches for known issues, post-mortems, and CVEs related to the affected service and incident type. Deduplicates results by URL. Results are formatted as a `combined_context` string and prepended to `web_context`.

**Output:** `WebSearchOutput` — results list (title, url, snippet), combined_context, queries_used.

### Ops Analyst (optional)

**Enabled by default.** Disabled if user removes `ops_analyst` from enabled_agents.
**Requires:** Ops Inspector MCP server running (auto-started if configured).

Uses four MCP tools (parse_stack_trace, calculate_error_rate, format_incident_brief, check_service_health) to analyse telemetry signals. Results are appended to `web_context`.

**Output:** `OpsAnalystOutput` — result string, tools_used list.

### Crew Intelligence (optional)

**Enabled by default.** Disabled if user removes `crew` from enabled_agents.

Runs a three-agent CrewAI crew:

1. **Researcher** — gathers known issues and documentation
2. **Analyst** — correlates signals from graph, web, and telemetry
3. **Writer** — synthesises a structured intelligence report

The crew report is appended to `web_context` as `=== CrewAI Intelligence Report ===`.

### Root Cause Finder

**Required.** Always runs for incident queries.

Takes the full accumulated context: query, service, severity, incident_type, graph_context, classification dict, and the entire `web_context` string (which includes web search, repo scout, terraform scout, ops diagnostics, crew report, and document markdown if uploaded).

**Output:** `RootCauseFinderOutput`:

- `primary_cause` — single sentence describing the root cause
- `causal_chain` — ordered list of `CausalFactor` (factor, confidence 0–1, evidence string)
- `contributing_factors` — secondary contributing factors
- `deployment_correlation` — bool: does a recent deployment correlate?
- `deployment_version` — version string if correlation found
- `timeline_reconstruction` — ordered list of events leading to the incident
- `confidence_score` — overall confidence (0.0–1.0)
- `reasoning` — extended reasoning trace

### Remediator

**Required.** Always runs for incident queries.

**Input:** Service, severity, primary_cause, causal_chain, blast_radius dict, deployment_correlation, deployment_version.

**Output:** `RemediatorOutput`:

- `immediate_actions` — ordered `RemediationStep` list (action, command, expected_outcome, risk_level, estimated_minutes)
- `rollback_steps` — rollback procedure steps
- `mitigation_steps` — longer-term mitigation actions
- `escalation_paths` — team escalation routes (team, contact, condition)
- `runbook_references` — relevant runbook URLs
- `estimated_resolution_minutes` — estimated MTTR
- `post_incident_actions` — post-mortem and follow-up tasks
- `summary` — single-paragraph remediation overview

### Conversationalist

**Required.** Runs on every turn — both incident and off-topic.

For incident queries: synthesises root_cause, remediation_steps, rollback_steps, timeline, blast_radius, causal_chain, and web_citations into a Markdown narrative. Also produces a `summary_for_history` (≤120 words) used for history compaction on subsequent turns.

For off-topic queries: generates a helpful direct response without fabricating incident analysis, setting `is_incident_relevant=False`. The pipeline short-circuits after this step without running entity extraction, graph traversal, or root cause analysis.

History compaction (`compact_history` in `utils.py`): conversation history beyond the last N turns is replaced with the stored `summary_for_history` value to keep the LLM context window bounded.

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

## Orchestrator and Streaming

`IncidentOrchestrator.run_with_stream()` is an async generator that yields `StreamEvent` objects. The SSE endpoint in `stream.py` iterates the generator and emits each event as `data: <json>\n\n`.

### StreamEvent structure

Every event has the same envelope:

```python
StreamEvent(
    event="step",          # step | graph | reasoning | result | error_event | done
    agent="classifier",    # agent key
    step="classify",       # step name within the agent
    status="complete",     # running | complete | error | skipped
    data={...},            # agent-specific payload
)
```

### data payload fields (present on all running/complete/error blocks)

| Field             | Present on | Description                                           |
| ----------------- | ---------- | ----------------------------------------------------- |
| `description`     | all        | Human-readable description of what the step does      |
| `input`           | all        | First 300 chars of the actual input sent to the agent |
| `output`          | complete   | First 300–500 chars of the agent's output             |
| `error`           | error      | Raw exception string                                  |
| `completed_steps` | complete   | List of all pipeline steps completed so far           |

Additional agent-specific fields (e.g. `causal_chain`, `blast_radius_count`, `tools_used`, `citations`) are also included and visible in the frontend explainability modal's "Raw agent data" section.

### SSE event flow per turn

```
session → orchestration_start(running) → orchestration_start(complete)
  → document_processing(running|skipped) → document_processing(complete|error)
  → classify(running) → classify(complete|error)
  → entity_extraction(running) → entity_extraction(complete|error)
  → repo_scouting(running|skipped) → repo_scouting(complete|error)
  → terraform_scouting(running|skipped) → terraform_scouting(complete|error)
  → neo4j_operation_plan(running) → graph_traversal(running) → graph_traversal(complete|error)
  → web_search(running|skipped) → web_search(complete|error)
  → ops_diagnostics(running|skipped) → ops_diagnostics(complete|error)
  → crew_enrichment(running|skipped) → crew_enrichment(complete|error)
  → root_cause_analysis(running) → root_cause_analysis(complete|error)
  → remediation(running) → remediation(complete|error)
  → natural_response(running) → natural_response(complete|error)
  → result(complete)
  → done
```

### IncidentState

`IncidentState` (in `orchestrator/models.py`) is the shared mutable dataclass accumulated across the entire turn:

```python
@dataclass
class IncidentState:
    query: str
    session_id: str
    service: str | None = None
    severity: str | None = None
    incident_type: str | None = None
    affected_components: list[str] = field(default_factory=list)
    entities: dict = field(default_factory=dict)
    classification: dict = field(default_factory=dict)
    graph_context: dict = field(default_factory=dict)
    document_context: str = ""
    document_context_chars: int = 0
    root_cause: str | None = None
    causal_chain: list[dict] = field(default_factory=list)
    remediation_steps: list[str] = field(default_factory=list)
    rollback_steps: list[str] = field(default_factory=list)
    escalation_paths: list[dict] = field(default_factory=list)
    runbook_references: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    web_citations: list[dict] = field(default_factory=list)
    natural_response: str | None = None
    conversation_summary: str | None = None
    is_incident_relevant: bool = True
    errors: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    # ... scout and analyst sub-fields
```

The final `result` event aggregates all state fields into a single JSON payload that the frontend uses to render the structured assistant message.

### Document context injection

When the SSE endpoint receives a non-empty `document_context` query parameter, it:

1. Adds `"document_processor"` to the `enabled_agents` set automatically.
2. Passes `document_context` into `IncidentOrchestrator.run_with_stream()`.
3. The orchestrator sets `state.document_context` and emits the Document Processor step events.
4. All downstream agents receive the document markdown prepended to the effective query.

---

## Neo4j Knowledge Graph

The knowledge graph is the core structural data store for service topology, ownership, historical incidents, runbooks, deployments, and configuration changes. It is populated by `app/db/neo4j_seed.py` and kept current by Celery periodic tasks.

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

```cypher
(Service)-[:DEPENDS_ON]->(Service)
(Service)-[:OWNED_BY]->(Team)
(Deployment)-[:DEPLOYED_TO]->(Service)
(Incident)-[:AFFECTS]->(Service)
(Runbook)-[:APPLIES_TO]->(Service)
(ConfigChange)-[:CHANGED]->(Service)
(WebKnowledge)-[:RELATES_TO]->(Service)
```

### Cypher queries executed per incident (Graph Analyzer)

1. `MATCH (s:Service {name: $service})-[:DEPENDS_ON]->(dep)` — direct downstream dependencies
2. `MATCH (caller)-[:DEPENDS_ON]->(s:Service {name: $service})` — upstream callers
3. `MATCH (s:Service {name: $service})-[:DEPENDS_ON*1..3]->(b)` — blast radius (3-hop transitive)
4. `MATCH (d:Deployment)-[:DEPLOYED_TO]->(b)` — recent deployments in blast radius
5. `MATCH (i:Incident)-[:AFFECTS]->(b)` — historical incidents in blast radius
6. `MATCH (r:Runbook)-[:APPLIES_TO]->(b)` — runbooks covering blast radius services
7. `MATCH (t:Team)-[:OWNED_BY]-(b)` — owning teams for blast radius services
8. `MATCH (c:ConfigChange)-[:CHANGED]->(b)` — config changes for blast radius services
9. `MATCH (i:Incident)-[:AFFECTS]->(e) WHERE e.name IN $entities` — cross-entity incidents from entity extraction

### Seeded topology

`neo4j_seed.py` creates a realistic microservices e-commerce stack with the following services: `checkout`, `payment`, `inventory`, `shipping`, `notification`, `user-service`, `product-catalog`, `search`, `recommendation`, `api-gateway`. All services have `DEPENDS_ON` relationships, `OWNED_BY` team relationships, and associated `Deployment`, `Incident`, `Runbook`, and `ConfigChange` nodes with realistic timestamps and metadata.

### Celery graph maintenance tasks

| Task                             | Schedule        | What it does                                                                                                        |
| -------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------- |
| `refresh_service_health`         | Every 15 min    | Fetches health signals (simulated) and updates Service node `status` properties                                     |
| `sync_web_intelligence_to_graph` | Every hour      | Creates `WebKnowledge` nodes from CVE feeds, post-mortems, and advisory sources and links them to affected services |
| `prune_stale_incidents`          | Daily 02:00 UTC | Deletes resolved `Incident` nodes older than 90 days to prevent graph bloat                                         |

The broker and result backend for all Celery tasks are Redis (`REDIS_URL`).

### Development without Neo4j

The `GraphAnalyzerAgent` catches connection errors and returns a mock `GraphAnalyzerQueryOutput` with a realistic stub topology. This allows full end-to-end testing of the pipeline without a running Neo4j instance. Set `NEO4J_URI` in `.env` to enable the real graph.

---

## Authentication and Authorization

The auth system lives in `app/services/auth_service.py` and `app/core/security.py`.

### Registration flow

1. Validate email uniqueness and username uniqueness in PostgreSQL.
2. Hash password with bcrypt.
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

All user input — both the `query` string and `document_context` (uploaded file markdown) — passes through `app/core/guardrails.py` **before** being stored in the database or forwarded to any LLM. Guardrail violations abort the entire SSE stream with an `error_event` containing `code: GUARDRAIL_VIOLATION`.

### apply_all(text) pipeline

```python
apply_all(text)
  → sanitise_input(text)        # strip null bytes and control characters
  → enforce_length(text)        # truncate to MAX_QUERY_LENGTH (4000 chars)
  → check_prompt_injection(text) # raise GuardrailViolation if injection matched
  → scrub_pii(text)             # redact PII (Presidio or regex fallback)
```

All four steps run on both `query` and `document_context` independently before they are combined.

### Injection patterns detected

The regex set in `check_prompt_injection` covers (case-insensitive, partial match):

- `ignore all previous instructions`
- `forget everything`
- `you are now`
- `pretend to be`
- `act as`
- `jailbreak`
- `bypass`
- `reveal your prompt`
- `system prompt`
- `disregard`
- `override`
- `new persona`
- and additional known attack patterns

### PII scrubbing

**With `microsoft-presidio` installed:** Uses spaCy NLP entity recognition for PERSON, EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IP_ADDRESS, US_SSN, IBAN_CODE, and more. Detected entities are replaced with `<REDACTED_TYPE>` placeholders.

**Regex fallback (no Presidio):** Matches and redacts:

- Email addresses: `[\w.-]+@[\w.-]+`
- IPv4 addresses: `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`

### Frontend guardrail handling

The SSE stream function in the frontend catches `error_event` messages with `code: GUARDRAIL_VIOLATION` and displays a system error message in the chat panel rather than treating it as an agent step failure. This gives users a clear, actionable message without leaking internal pipeline details.

---

## MCP Integrations

MCP (Model Context Protocol) is an open standard for connecting LLM agents to external tools and data sources through a unified client–server protocol. Ops-Pilot uses MCP for three integrations: GitHub, Terraform, and the custom Ops Inspector diagnostic server.

### MCPClientManager

`mcp_servers/mcp_client_manager.py` manages the lifecycle of MCP client connections:

- Reads `servers.json` for server configurations
- Expands `${VAR}` environment variable references in `env` blocks at connection time
- Starts MCP server processes (via `stdio` transport for local servers)
- Maintains a dict of `{server_name: MCPClient}` instances
- Provides `get_tools(server_name)` to list available tools
- Provides `call_tool(server_name, tool_name, args)` for tool invocation
- Handles connection failure gracefully — agents log a warning and produce degraded output rather than crashing

Each MCP-backed agent (`RepoScoutAgent`, `TerraformScoutAgent`, `OpsAnalystAgent`) holds an `asyncio.Lock` for lazy one-time async initialisation and a `_tool_names` list populated after the MCP connection is established.

### servers.json structure

```json
{
  "github": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_TOKEN": "${GITHUB_TOKEN}"
    }
  },
  "terraform": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-terraform"],
    "env": {}
  },
  "ops-inspector": {
    "command": "python",
    "args": ["-m", "mcp_servers.servers.ops_inspector"]
  }
}
```

### GitHub MCP (Repo Scout)

Uses `@modelcontextprotocol/server-github`. Requires `GITHUB_TOKEN` (Personal Access Token with `repo` and `read:org` scopes). Tools used: `list_commits`, `list_pull_requests`, `list_check_runs`. The service name is split on `/` to derive `owner/repo`.

### Terraform MCP (Terraform Scout)

Uses a Terraform MCP server. Inspects workspace state for recent `plan` and `apply` runs, detects resource drift, and summarises IaC changes. No additional credentials required beyond workspace access.

### Ops Inspector MCP Server (custom)

`mcp_servers/servers/ops_inspector.py` is a custom MCP server built with the `mcp` Python SDK. It exposes four tools:

| Tool                    | Input                                             | Output                                        |
| ----------------------- | ------------------------------------------------- | --------------------------------------------- |
| `parse_stack_trace`     | `stack_trace: str`                                | Exception type, root frame, likely cause      |
| `calculate_error_rate`  | `errors: int, requests: int, window_seconds: int` | Error rate %, severity label, SLO breach flag |
| `format_incident_brief` | `service, severity, description, timestamp`       | Structured incident brief dict                |
| `check_service_health`  | `metrics: dict`                                   | Health status, anomaly list, recommendation   |

The Ops Inspector server is started automatically by the `MCPClientManager` as a subprocess using Python's `mcp` package stdio transport.

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
