# Ops-Pilot Backend

FastAPI + LangGraph + CrewAI + Neo4j + PostgreSQL + Redis/Celery

## Setup (local dev)

    cp .env.example .env
    # Fill in OPENAI_API_KEY and SECRET_KEY (openssl rand -hex 32)

    uv sync

    # Start databases
    docker-compose up -d postgres neo4j redis

    # Run migrations
    uv run alembic upgrade head

    # Seed Neo4j knowledge graph
    uv run python -m app.db.neo4j_seed

    # Start API
    uv run uvicorn app.main:app --reload --port 8000

    # Start Celery (separate terminals)
    uv run celery -A app.tasks.celery_app worker --loglevel=info
    uv run celery -A app.tasks.celery_app beat   --loglevel=info

    # Run tests
    uv run pytest tests/ -v

## Alembic Migrations

    uv run alembic upgrade head                                  # apply
    uv run alembic revision --autogenerate -m "describe change"  # generate
    uv run alembic downgrade -1                                  # rollback
    uv run alembic current                                       # check

## Agent Pipeline

    ClassifierAgent
      → EntityExtractorAgent  (renamed from SearcherAgent)
        → GraphAnalyzerAgent  (deep Neo4j traversal)
          → WebSearcherAgent  (DuckDuckGo)
            → IncidentAnalysisCrew (CrewAI)
              → RootCauseFinderAgent
                → RemediatorAgent

All agents extend BaseAgent (app/core/base_agent.py).
All LLM calls use llm.with_structured_output(PydanticModel).

## LLM Provider Selection

Set in .env:

    LLM_PROVIDER=openai      # default
    LLM_PROVIDER=anthropic
    LLM_PROVIDER=google

## Security Guardrails

All user input passes through app/core/guardrails.py:
- Sanitise control characters
- Enforce length cap (MAX_QUERY_LENGTH)
- Detect prompt injection patterns
- Scrub PII (Presidio when installed, regex fallback)

## API Structure

    app/api/__init__.py     <- single aggregated router
    app/api/uris.py         <- URI constants (no magic strings)
    app/api/dtos.py         <- re-exported schema DTOs
    app/api/deps.py         <- get_current_user, get_optional_user
    app/api/routes/
        auth.py             <- /api/v1/auth/*
        incident.py         <- /api/v1/incident/*
        chat.py             <- /api/v1/chat/*
        stream.py           <- /api/v1/stream/*
        health.py           <- /health

## Neo4j Knowledge Graph

The GraphAnalyzerAgent performs 9 Cypher queries per incident:
1. Direct dependencies
2. Upstream callers
3. Full blast radius (3-hop transitive closure)
4. Deployments across blast-radius services
5. Historical incidents
6. Associated runbooks
7. Team ownership
8. Configuration change events
9. Cross-entity incidents

Web intelligence is written back to Neo4j as WebKnowledge nodes
by the Celery sync_web_intelligence_to_graph task.