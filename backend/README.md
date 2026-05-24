# Ops-Pilot Backend

FastAPI + LangGraph multi-agent incident response backend.

## Setup

```bash
cp .env.example .env          # fill in OPENAI_API_KEY
uv sync                       # install from pyproject.toml
uv run python -m app.db.migrations
uv run python -m app.db.neo4j_seed
uv run uvicorn app.main:app --reload --port 8000
```

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /api/incident/analyze | Sync analysis |
| GET | /api/stream/incident?query=... | SSE streaming |
| POST | /api/chat/new | Create session |
| GET | /api/chat/{id}/messages | Get messages |
| GET | /api/chat/{id}/executions | Execution trace |

## Tests

```bash
uv run pytest tests/ -v
```

## Agent Architecture

Each agent: `llm.with_structured_output(PydanticModel)` — no free-text parsing.

1. **ClassifierAgent** → service, severity, type
2. **SearcherAgent** → entities, deployments, metrics
3. **GraphAgent** → Neo4j traversal, blast radius
4. **RootCauseAgent** → causal chain, deployment correlation
5. **RemediationAgent** → rollback steps, runbooks, escalation paths