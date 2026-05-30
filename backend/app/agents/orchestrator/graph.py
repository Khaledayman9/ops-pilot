from __future__ import annotations

import json
from collections.abc import AsyncGenerator

from app.schemas.stream import StreamEvent
from logger import logger

from ..classifier import ClassificationInput, ClassifierAgent
from ..conversationalist import ConversationalistAgent, ConversationalistInput
from ..conversationalist.models import ChatTurn
from ..crew.incident_crew import IncidentAnalysisCrew
from ..entity_extractor import EntityExtractorAgent, EntityExtractorInput
from ..graph_analyzer import GraphAnalyzerAgent, GraphAnalyzerQueryInput
from ..ops_analyst import AnalysisTask, OpsAnalystAgent, OpsAnalystInput
from ..remediator import RemediatorAgent, RemediatorInput
from ..repo_scouter import RepoScoutAgent, RepoScoutInput
from ..root_cause_finder import RootCauseFinderAgent, RootCauseFinderInput
from ..terraform_scouter import TerraformScoutAgent, TerraformScoutInput
from ..web_searcher import WebSearcherAgent, WebSearchInput
from .models import IncidentState


_MAX_HISTORY_TURNS = 10

DEFAULT_ENABLED_AGENTS = {
    "orchestrator",
    "document_processor",
    "classifier",
    "entity_extractor",
    "repo_scout",
    "terraform_scout",
    "graph_analyzer",
    "web_searcher",
    "ops_analyst",
    "crew",
    "root_cause_finder",
    "remediator",
    "conversationalist",
}

REQUIRED_AGENTS = {
    "orchestrator",
    "classifier",
    "entity_extractor",
    "graph_analyzer",
    "root_cause_finder",
    "remediator",
    "conversationalist",
}


def _build_analysis_context(state: IncidentState) -> str:
    """Flatten key pipeline outputs into a single text block for the conversationalist."""
    parts: list[str] = []

    if state.service:
        parts.append(f"Service: {state.service}")
    if state.severity:
        parts.append(f"Severity: {state.severity}")
    if state.incident_type:
        parts.append(f"Incident type: {state.incident_type}")
    if state.root_cause:
        parts.append(f"Root cause: {state.root_cause}")
    if state.causal_chain:
        chain = "; ".join(f["factor"] for f in state.causal_chain if "factor" in f)
        parts.append(f"Causal chain: {chain}")
    if state.remediation_steps:
        steps = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(state.remediation_steps))
        parts.append(f"Remediation steps:\n{steps}")
    if state.rollback_steps:
        steps = "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(state.rollback_steps))
        parts.append(f"Rollback steps:\n{steps}")
    if state.timeline:
        parts.append(f"Timeline: {'; '.join(state.timeline)}")
    if state.repo_scout_summary:
        parts.append(f"Repo scout: {state.repo_scout_summary[:400]}")
    if state.terraform_scout_summary:
        parts.append(f"Terraform scout: {state.terraform_scout_summary[:400]}")
    if state.ops_analyst_result:
        parts.append(f"Ops diagnostics: {state.ops_analyst_result[:400]}")

    return "\n".join(parts)


def _compact_history(raw_history: list[dict]) -> list[ChatTurn]:
    """
    Convert raw stored message dicts into ChatTurn objects.
    Keeps the most recent _MAX_HISTORY_TURNS turns to stay within context limits.
    If a message contains a compacted summary marker, prefer that over the raw content.
    """
    turns: list[ChatTurn] = []
    for msg in raw_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "assistant":
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "conversation_summary" in parsed:
                    content = parsed["conversation_summary"]
                elif isinstance(parsed, list):
                    content = content[:300]
            except (json.JSONDecodeError, ValueError):
                content = content[:300]
        turns.append(ChatTurn(role=role, content=content))

    return turns[-_MAX_HISTORY_TURNS:]


class IncidentOrchestrator:
    def __init__(self) -> None:
        self._classifier = ClassifierAgent()
        self._extractor = EntityExtractorAgent()
        self._repo_scout = RepoScoutAgent()
        self._terraform_scout = TerraformScoutAgent()
        self._graph = GraphAnalyzerAgent()
        self._web_searcher = WebSearcherAgent()
        self._ops_analyst = OpsAnalystAgent()
        self._crew = IncidentAnalysisCrew()
        self._root_cause = RootCauseFinderAgent()
        self._remediator = RemediatorAgent()
        self._conversationalist = ConversationalistAgent()

    async def run_with_stream(
        self,
        query: str,
        session_id: str,
        document_context: str = "",
        enabled_agents: set[str] | None = None,
        chat_history: list[dict] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        enabled_agents = (enabled_agents or DEFAULT_ENABLED_AGENTS) | REQUIRED_AGENTS

        state = IncidentState(query=query, session_id=session_id)
        state.document_context = document_context or ""
        state.document_context_chars = len(state.document_context)

        compacted_history = _compact_history(chat_history or [])

        effective_query = query
        if state.document_context:
            effective_query = (
                f"{query}\n\n"
                "=== Uploaded Document Context Converted By Document Processor ===\n"
                f"{state.document_context}"
            )

        yield StreamEvent(
            event="step",
            agent="orchestrator",
            step="orchestration_start",
            status="running",
            data={
                "message": "Starting orchestrator turn",
                "description": "Routes the incoming query through the full multi-agent pipeline, deciding which agents to invoke based on enabled config.",
                "input": query[:300],
                "enabled_agents": sorted(enabled_agents),
                "output": f"Pipeline starting with {len(enabled_agents)} agents enabled",
            },
        )

        if state.document_context:
            state.completed_steps.append("document_processing")
            yield StreamEvent(
                event="step",
                agent="document_processor",
                step="document_processing",
                status="complete",
                data={
                    "message": "Document markdown attached to this orchestration turn",
                    "description": "Converts uploaded files (PDF, DOCX, etc.) to markdown and injects them into the pipeline context for all downstream agents.",
                    "input": f"User query + document context",
                    "output": f"Attached {state.document_context_chars} chars of document markdown to pipeline",
                    "characters": state.document_context_chars,
                    "completed_steps": list(state.completed_steps),
                },
            )

        yield StreamEvent(
            event="step",
            agent="classifier",
            step="classify",
            status="running",
            data={
                "message": "Classifying incident",
                "description": "Uses an LLM to extract service name, severity (P0-P3), incident type, affected components, and confidence score from the raw query.",
                "input": effective_query[:300],
            },
        )
        try:
            out = await self._classifier.run(ClassificationInput(query=effective_query))
            state.service = out.service
            state.severity = out.severity
            state.incident_type = out.incident_type
            state.affected_components = out.affected_components
            state.trigger_event = out.trigger_event
            state.classification = out.model_dump()
            state.completed_steps.append("classify")
            yield StreamEvent(
                event="step",
                agent="classifier",
                step="classify",
                status="complete",
                data={
                    **state.classification,
                    "description": "Incident classified — severity, service, and type identified for downstream agents.",
                    "output": f"Service: {out.service} | Severity: {out.severity} | Type: {out.incident_type}",
                    "completed_steps": list(state.completed_steps),
                },
            )
        except Exception as exc:
            logger.error(f"[Orchestrator] Classifier: {exc}")
            state.errors.append(str(exc))
            yield StreamEvent(
                event="step",
                agent="classifier",
                step="classify",
                status="error",
                data={"error": str(exc)},
            )

        is_incident_query = bool(
            state.service
            and state.service.lower() not in {"none", "unknown", "n/a", ""}
            and state.classification.get("confidence", 1.0) > 0.25
        )

        if not is_incident_query:
            yield StreamEvent(
                event="step",
                agent="conversationalist",
                step="natural_response",
                status="running",
                data={
                    "message": "Generating natural language response for off-topic query",
                    "description": "Query was not incident-related; conversationalist generates a direct chat response without running the full pipeline.",
                },
            )
            try:
                conv_out = await self._conversationalist.run(
                    ConversationalistInput(
                        query=query,
                        history=compacted_history,
                        incident_structured=None,
                        web_citations=[],
                        is_incident_query=False,
                        analysis_context="",
                    )
                )
                state.natural_response = conv_out.natural_response
                state.is_incident_relevant = False
                state.conversation_summary = conv_out.summary_for_history
                state.completed_steps.append("natural_response")
                yield StreamEvent(
                    event="step",
                    agent="conversationalist",
                    step="natural_response",
                    status="complete",
                    data={"message": "Natural response ready"},
                )
            except Exception as exc:
                logger.error(f"[Orchestrator] Conversationalist (off-topic): {exc}")
                state.errors.append(str(exc))
                state.natural_response = (
                    "I'm here to help with incident analysis. "
                    "Could you describe a production incident or system issue?"
                )
                state.is_incident_relevant = False
                yield StreamEvent(
                    event="step",
                    agent="conversationalist",
                    step="natural_response",
                    status="error",
                    data={"error": str(exc)},
                )

            yield StreamEvent(
                event="result",
                agent="orchestrator",
                step="complete",
                status="complete",
                data={
                    "session_id": state.session_id,
                    "is_incident_relevant": False,
                    "natural_response": state.natural_response,
                    "conversation_summary": state.conversation_summary,
                    "completed_steps": state.completed_steps,
                    "errors": state.errors,
                },
            )
            return

        yield StreamEvent(
            event="step",
            agent="entity_extractor",
            step="entity_extraction",
            status="running",
            data={
                "message": "Extracting entities",
                "description": "Parses the query to extract structured entities: services, deployments, metrics, error codes, time ranges, and search keywords for downstream graph and web queries.",
                "input": f"Service: {state.service} | Type: {state.incident_type} | Query: {query[:200]}",
            },
        )
        try:
            out = await self._extractor.run(
                EntityExtractorInput(
                    query=effective_query,
                    service=state.service or "unknown",
                    incident_type=state.incident_type or "unknown",
                )
            )
            state.entities = out.entities.model_dump()
            state.completed_steps.append("entity_extraction")
            yield StreamEvent(
                event="step",
                agent="entity_extractor",
                step="entity_extraction",
                status="complete",
                data={
                    **state.entities,
                    "description": "Entities extracted and structured for graph traversal and web search.",
                    "output": out.context_summary[:300],
                    "search_queries": out.search_queries,
                    "completed_steps": list(state.completed_steps),
                },
            )
        except Exception as exc:
            logger.error(f"[Orchestrator] EntityExtractor: {exc}")
            state.errors.append(str(exc))
            yield StreamEvent(
                event="step",
                agent="entity_extractor",
                step="entity_extraction",
                status="error",
                data={"error": str(exc)},
            )

        if "repo_scout" in enabled_agents:
            yield StreamEvent(
                event="step",
                agent="repo_scout",
                step="repo_scouting",
                status="running",
                data={
                    "message": "Scouting GitHub repository for recent activity",
                    "description": "Scans the GitHub repo associated with the affected service for recent commits, open PRs, and failing CI checks that may correlate with the incident.",
                    "input": f"Service: {state.service} | Incident type: {state.incident_type}",
                    "steps": ["Resolve owner/repo from service name", "Fetch recent commits", "Check open PRs", "Check failing CI checks", "Summarize findings"],
                },
            )
            try:
                service_slug = (state.service or "unknown").replace(" ", "-").lower()
                parts = service_slug.split("/", 1)
                owner = parts[0] if len(parts) == 2 else "unknown"
                repo = parts[1] if len(parts) == 2 else service_slug

                scout_out = await self._repo_scout.run(
                    RepoScoutInput(
                        owner=owner,
                        repo=repo,
                        task="summarize",
                        extra_context=(
                            f"Incident type: {state.incident_type or 'unknown'}. "
                            f"Document context chars: {state.document_context_chars}. "
                            "Focus on recent commits, open PRs, and failing checks."
                        ),
                    )
                )
                state.repo_scout_summary = scout_out.summary
                state.repo_scout_tools_used = scout_out.tools_used
                state.completed_steps.append("repo_scouting")
                yield StreamEvent(
                    event="step",
                    agent="repo_scout",
                    step="repo_scouting",
                    status="complete",
                    data={
                        "description": "Repository scan complete — recent code changes and CI status collected.",
                        "input": f"{owner}/{repo}",
                        "output": scout_out.summary[:400],
                        "summary": scout_out.summary[:500],
                        "tools_used": scout_out.tools_used,
                        "completed_steps": list(state.completed_steps),
                    },
                )
            except Exception as exc:
                logger.warning(f"[Orchestrator] RepoScout: {exc} - continuing without GitHub data")
                state.errors.append(f"repo_scout: {exc}")
                yield StreamEvent(
                    event="step",
                    agent="repo_scout",
                    step="repo_scouting",
                    status="error",
                    data={"error": str(exc)},
                )
        else:
            yield StreamEvent(
                event="step",
                agent="repo_scout",
                step="repo_scouting",
                status="skipped",
                data={"message": "Repo Scanner disabled by user"},
            )

        if "terraform_scout" in enabled_agents:
            yield StreamEvent(
                event="step",
                agent="terraform_scout",
                step="terraform_scouting",
                status="running",
                data={
                    "message": "Inspecting Terraform/IaC context",
                    "description": "Checks Terraform workspace state for recent plan/apply runs and infrastructure drift that may have caused or contributed to the incident.",
                    "input": f"Workspace: {state.service or 'default'} | Query: {query[:150]}",
                    "steps": ["Load workspace state", "Detect recent plan/apply runs", "Identify drift", "Correlate with incident", "Summarize IaC findings"],
                },
            )
            try:
                terraform_out = await self._terraform_scout.run(
                    TerraformScoutInput(
                        task="summarize",
                        workspace=state.service or "default",
                        extra_context=effective_query,
                    )
                )
                state.terraform_scout_summary = terraform_out.summary
                state.terraform_scout_tools_used = terraform_out.tools_used
                state.completed_steps.append("terraform_scouting")
                yield StreamEvent(
                    event="step",
                    agent="terraform_scout",
                    step="terraform_scouting",
                    status="complete",
                    data={
                        "description": "IaC inspection complete — infrastructure drift and recent applies recorded.",
                        "input": f"Workspace: {state.service or 'default'}",
                        "output": terraform_out.summary[:400],
                        "summary": terraform_out.summary[:500],
                        "tools_used": terraform_out.tools_used,
                        "completed_steps": list(state.completed_steps),
                    },
                )
            except Exception as exc:
                logger.warning(
                    f"[Orchestrator] TerraformScout: {exc} - continuing without IaC data"
                )
                state.errors.append(f"terraform_scout: {exc}")
                yield StreamEvent(
                    event="step",
                    agent="terraform_scout",
                    step="terraform_scouting",
                    status="error",
                    data={"error": str(exc)},
                )
        else:
            yield StreamEvent(
                event="step",
                agent="terraform_scout",
                step="terraform_scouting",
                status="skipped",
                data={"message": "Terraform Scanner disabled by user"},
            )

        yield StreamEvent(
            event="step",
            agent="graph_analyzer",
            step="neo4j_operation_plan",
            status="running",
            data={
                "message": "Preparing graph traversal queries",
                "description": "Plans the set of Cypher queries to execute against the Neo4j service dependency graph to map blast radius, ownership, and related incidents.",
                "input": f"Service: {state.service} | Entities: {state.entities.get('services', [])}",
                "steps": [
                    "MATCH upstream dependencies",
                    "MATCH downstream blast radius",
                    "MATCH recent deployments",
                    "MATCH open incidents",
                    "MATCH runbook references",
                    "MATCH ownership records",
                    "MATCH config changes",
                ],
                "output": f"Querying Neo4j for service '{state.service}' dependency graph",
            },
        )

        yield StreamEvent(
            event="step",
            agent="graph_analyzer",
            step="graph_traversal",
            status="running",
            data={
                "message": "Running Neo4j graph traversal",
                "description": "Executes Cypher queries against Neo4j to find upstream/downstream services, blast radius, recent deployments, runbooks, and ownership for the affected service.",
                "input": f"Service: {state.service} | Incident type: {state.incident_type}",
            },
        )
        try:
            out = await self._graph.run(
                GraphAnalyzerQueryInput(
                    service=state.service or "unknown",
                    entities=state.entities.get("services", []),
                    incident_type=state.incident_type or "unknown",
                )
            )
            state.graph_context = out.model_dump()
            state.completed_steps.append("graph_traversal")
            yield StreamEvent(
                event="graph",
                agent="graph_analyzer",
                step="graph_traversal",
                status="complete",
                data={
                    **state.graph_context,
                    "description": "Graph traversal complete — service topology, blast radius, and ownership mapped.",
                    "output": f"Blast radius: {state.graph_context.get('blast_radius_count', 0)} nodes | Upstream: {len(state.graph_context.get('upstream_services', []))} | Downstream: {len(state.graph_context.get('downstream_services', []))}",
                    "completed_steps": list(state.completed_steps),
                },
            )
        except Exception as exc:
            logger.error(f"[Orchestrator] GraphAnalyzer: {exc}")
            state.errors.append(str(exc))
            yield StreamEvent(
                event="step",
                agent="graph_analyzer",
                step="graph_traversal",
                status="error",
                data={"error": str(exc)},
            )

        web_context = "No supplementary web intelligence available."
        if state.document_context:
            web_context = (
                f"{web_context}\n\n=== Uploaded Document Evidence ===\n{state.document_context}"
            )

        if state.repo_scout_summary:
            web_context = (
                f"{web_context}\n\n=== Repo Scout Evidence ===\n{state.repo_scout_summary}"
            )

        if state.terraform_scout_summary:
            web_context = f"{web_context}\n\n=== Terraform Scout Evidence ===\n{state.terraform_scout_summary}"

        if "web_searcher" in enabled_agents:
            _ws_query = f"{state.service} {state.incident_type} incident"
            yield StreamEvent(
                event="step",
                agent="web_searcher",
                step="web_search",
                status="running",
                data={
                    "message": "Searching web for known issues",
                    "description": "Runs DuckDuckGo searches for known issues, post-mortems, and bug reports related to the affected service and incident type to enrich analysis context.",
                    "input": _ws_query,
                    "queries": [
                        _ws_query,
                        f"{state.service} {state.incident_type} bug",
                        f"{state.service} incident post-mortem",
                    ],
                },
            )
            try:
                web_out = await self._web_searcher.run(
                    WebSearchInput(query=_ws_query),
                    service=state.service or "unknown",
                    incident_type=state.incident_type or "unknown",
                    deployment_version=state.deployment_version,
                )
                web_context = f"{web_out.combined_context}\n\n{web_context}"
                state.web_citations = [
                    {"title": r.title, "url": r.url, "snippet": r.snippet} for r in web_out.results
                ]
                state.completed_steps.append("web_search")
                yield StreamEvent(
                    event="step",
                    agent="web_searcher",
                    step="web_search",
                    status="complete",
                    data={
                        "description": "Web search complete — external signals and known issues collected.",
                        "input": _ws_query,
                        "queries_used": web_out.queries_used,
                        "results_count": len(web_out.results),
                        "output": f"Found {len(web_out.results)} results. Top: {web_out.results[0].title if web_out.results else 'none'}",
                        "citations": state.web_citations[:5],
                        "completed_steps": list(state.completed_steps),
                    },
                )
            except Exception as exc:
                logger.warning(f"[Orchestrator] WebSearcher: {exc}")
                state.errors.append(str(exc))
                yield StreamEvent(
                    event="step",
                    agent="web_searcher",
                    step="web_search",
                    status="error",
                    data={"error": str(exc)},
                )
        else:
            yield StreamEvent(
                event="step",
                agent="web_searcher",
                step="web_search",
                status="skipped",
                data={"message": "Web Intelligence disabled by user"},
            )

        if "ops_analyst" in enabled_agents:
            yield StreamEvent(
                event="step",
                agent="ops_analyst",
                step="ops_diagnostics",
                status="running",
                data={
                    "message": "Running operational diagnostics",
                    "description": "Queries observability tools (metrics, traces, logs) to detect error rate spikes, latency anomalies, and saturation signals for the affected service.",
                    "input": f"Service: {state.service} | Query: {query[:200]}",
                    "steps": ["Query metrics store", "Check error rates", "Check latency percentiles", "Check saturation signals", "Summarize telemetry findings"],
                },
            )
            try:
                analyst_out = await self._ops_analyst.run(
                    OpsAnalystInput(
                        task=AnalysisTask.GENERAL,
                        payload=effective_query,
                        service_name=state.service or "unknown",
                    )
                )
                state.ops_analyst_result = analyst_out.result
                state.ops_analyst_tools_used = analyst_out.tools_used
                if analyst_out.result:
                    web_context = f"{web_context}\n\n=== Ops Diagnostics ===\n{analyst_out.result}"
                state.completed_steps.append("ops_diagnostics")
                yield StreamEvent(
                    event="step",
                    agent="ops_analyst",
                    step="ops_diagnostics",
                    status="complete",
                    data={
                        "description": "Telemetry diagnostics complete — error rates, latency, and saturation signals recorded.",
                        "input": f"Service: {state.service}",
                        "output": analyst_out.result[:400] if analyst_out.result else "No telemetry anomalies detected",
                        "result": analyst_out.result[:500],
                        "tools_used": analyst_out.tools_used,
                        "completed_steps": list(state.completed_steps),
                    },
                )
            except Exception as exc:
                logger.warning(f"[Orchestrator] OpsAnalyst: {exc} - continuing without diagnostics")
                state.errors.append(f"ops_analyst: {exc}")
                yield StreamEvent(
                    event="step",
                    agent="ops_analyst",
                    step="ops_diagnostics",
                    status="error",
                    data={"error": str(exc)},
                )
        else:
            yield StreamEvent(
                event="step",
                agent="ops_analyst",
                step="ops_diagnostics",
                status="skipped",
                data={"message": "Ops Analyst disabled by user"},
            )

        if "crew" in enabled_agents:
            yield StreamEvent(
                event="step",
                agent="crew",
                step="crew_enrichment",
                status="running",
                data={
                    "message": "Running CrewAI intelligence crew",
                    "description": "Runs a multi-agent CrewAI crew (Researcher → Analyst → Writer) to gather, correlate, and synthesize external intelligence about the incident.",
                    "input": f"Service: {state.service} | Type: {state.incident_type} | Query: {query[:150]}",
                    "steps": ["Researcher agent: gather known issues", "Analyst agent: correlate signals", "Writer agent: synthesize intelligence report"],
                },
            )
            try:
                crew_report = await self._crew.run(
                    service=state.service or "unknown",
                    incident_type=state.incident_type or "unknown",
                    query=effective_query,
                    deployment_version=state.deployment_version,
                    graph_summary=state.graph_context.get("graph_summary", ""),
                )
                web_context = f"{web_context}\n\n=== CrewAI Intelligence Report ===\n{crew_report}"
                state.completed_steps.append("crew_enrichment")
                yield StreamEvent(
                    event="step",
                    agent="crew",
                    step="crew_enrichment",
                    status="complete",
                    data={
                        "description": "CrewAI intelligence report synthesized and added to analysis context.",
                        "input": f"Service: {state.service} | Type: {state.incident_type}",
                        "output": crew_report[:400] if crew_report else "No crew report generated",
                        "report_length": len(crew_report),
                        "completed_steps": list(state.completed_steps),
                    },
                )
            except Exception as exc:
                logger.warning(f"[Orchestrator] Crew: {exc}")
                state.errors.append(str(exc))
                yield StreamEvent(
                    event="step",
                    agent="crew",
                    step="crew_enrichment",
                    status="error",
                    data={"error": str(exc)},
                )
        else:
            yield StreamEvent(
                event="step",
                agent="crew",
                step="crew_enrichment",
                status="skipped",
                data={"message": "Crew Intelligence disabled by user"},
            )

        yield StreamEvent(
            event="step",
            agent="root_cause_finder",
            step="root_cause_analysis",
            status="running",
            data={
                "message": "Running root cause analysis",
                "description": "Uses an LLM with full pipeline context (graph, web, telemetry, repo) to identify the primary root cause, build a causal chain, and reconstruct the incident timeline.",
                "input": f"Service: {state.service} | Severity: {state.severity} | Type: {state.incident_type}",
                "graph_nodes": state.graph_context.get("blast_radius_count", 0),
            },
        )
        try:
            out = await self._root_cause.run(
                RootCauseFinderInput(
                    query=effective_query,
                    service=state.service or "unknown",
                    incident_type=state.incident_type or "unknown",
                    severity=state.severity or "P2",
                    graph_context=state.graph_context,
                    classification=state.classification,
                ),
                web_context=web_context,
            )
            state.root_cause = out.primary_cause
            state.causal_chain = [f.model_dump() for f in out.causal_chain]
            state.deployment_correlation = out.deployment_correlation
            state.deployment_version = out.deployment_version
            state.timeline = out.timeline_reconstruction
            state.completed_steps.append("root_cause_analysis")
            yield StreamEvent(
                event="reasoning",
                agent="root_cause_finder",
                step="root_cause_analysis",
                status="complete",
                data={
                    **out.model_dump(),
                    "description": "Root cause identified — causal chain and timeline reconstruction complete.",
                    "output": out.primary_cause[:300],
                    "causal_chain_summary": [f.factor for f in out.causal_chain],
                    "completed_steps": list(state.completed_steps),
                },
            )
        except Exception as exc:
            logger.error(f"[Orchestrator] RootCauseFinder: {exc}")
            state.errors.append(str(exc))
            yield StreamEvent(
                event="step",
                agent="root_cause_finder",
                step="root_cause_analysis",
                status="error",
                data={"error": str(exc)},
            )

        yield StreamEvent(
            event="step",
            agent="remediator",
            step="remediation",
            status="running",
            data={
                "message": "Generating remediation plan",
                "description": "Generates an actionable remediation plan including immediate actions, rollback steps, escalation paths, and runbook references based on the identified root cause.",
                "input": f"Root cause: {state.root_cause or 'Unknown'} | Service: {state.service} | Severity: {state.severity}",
            },
        )
        try:
            out = await self._remediator.run(
                RemediatorInput(
                    service=state.service or "unknown",
                    severity=state.severity or "P2",
                    primary_cause=state.root_cause or "Unknown",
                    causal_chain=state.causal_chain,
                    blast_radius=state.graph_context,
                    deployment_correlation=state.deployment_correlation,
                    deployment_version=state.deployment_version,
                )
            )
            state.remediation_steps = [s.action for s in out.immediate_actions]
            state.rollback_steps = [s.action for s in out.rollback_steps]
            state.escalation_paths = [ep.model_dump() for ep in out.escalation_paths]
            state.runbook_references = out.runbook_references
            state.completed_steps.append("remediation")
            yield StreamEvent(
                event="step",
                agent="remediator",
                step="remediation",
                status="complete",
                data={
                    **out.model_dump(),
                    "description": "Remediation plan complete — immediate actions, rollback steps, and escalation paths generated.",
                    "output": f"{len(state.remediation_steps)} immediate actions | {len(state.rollback_steps)} rollback steps",
                    "immediate_actions_summary": state.remediation_steps[:5],
                    "completed_steps": list(state.completed_steps),
                },
            )
        except Exception as exc:
            logger.error(f"[Orchestrator] Remediator: {exc}")
            state.errors.append(str(exc))
            yield StreamEvent(
                event="step",
                agent="remediator",
                step="remediation",
                status="error",
                data={"error": str(exc)},
            )

        yield StreamEvent(
            event="step",
            agent="conversationalist",
            step="natural_response",
            status="running",
            data={
                "message": "Generating natural language explanation",
                "description": "Synthesizes all pipeline outputs into a coherent, human-readable incident narrative using an LLM, including citations and a conversation summary for history.",
                "input": f"Root cause: {state.root_cause or 'unknown'} | Remediation steps: {len(state.remediation_steps)} | Service: {state.service}",
                "steps": ["Synthesize pipeline outputs", "Generate human-readable narrative", "Include citations", "Summarize for history"],
            },
        )

        incident_structured = {
            "service": state.service,
            "severity": state.severity,
            "classification": state.classification,
            "root_cause": state.root_cause,
            "causal_chain": state.causal_chain,
            "timeline": state.timeline,
            "blast_radius": {
                "count": state.graph_context.get("blast_radius_count", 0),
                "upstream": state.graph_context.get("upstream_services", []),
                "downstream": state.graph_context.get("downstream_services", []),
            },
            "remediation_steps": state.remediation_steps,
            "rollback_steps": state.rollback_steps,
            "escalation_paths": state.escalation_paths,
            "runbook_references": state.runbook_references,
            "deployment_correlation": state.deployment_correlation,
            "deployment_version": state.deployment_version,
        }

        try:
            conv_out = await self._conversationalist.run(
                ConversationalistInput(
                    query=query,
                    history=compacted_history,
                    incident_structured=incident_structured,
                    web_citations=state.web_citations,
                    is_incident_query=True,
                    analysis_context=_build_analysis_context(state),
                )
            )
            state.natural_response = conv_out.natural_response
            state.is_incident_relevant = conv_out.is_incident_relevant
            state.conversation_summary = conv_out.summary_for_history
            state.completed_steps.append("natural_response")
            yield StreamEvent(
                event="step",
                agent="conversationalist",
                step="natural_response",
                status="complete",
                data={
                    "description": "Natural language narrative generated and ready to display.",
                    "input": f"Root cause: {state.root_cause or 'unknown'} | Service: {state.service}",
                    "output": state.natural_response[:400] if state.natural_response else "Response generated",
                    "message": "Natural response generated",
                    "completed_steps": list(state.completed_steps),
                },
            )
        except Exception as exc:
            logger.error(f"[Orchestrator] Conversationalist: {exc}")
            state.errors.append(str(exc))
            state.natural_response = "Analysis complete. Please review the structured output above."
            yield StreamEvent(
                event="step",
                agent="conversationalist",
                step="natural_response",
                status="error",
                data={"error": str(exc)},
            )

        yield StreamEvent(
            event="result",
            agent="orchestrator",
            step="complete",
            status="complete",
            data={
                "session_id": state.session_id,
                "is_incident_relevant": state.is_incident_relevant,
                "natural_response": state.natural_response,
                "conversation_summary": state.conversation_summary,
                "service": state.service,
                "severity": state.severity,
                "classification": state.classification,
                "document_context_chars": state.document_context_chars,
                "graph_context": state.graph_context,
                "repo_scout": {
                    "summary": state.repo_scout_summary,
                    "tools_used": state.repo_scout_tools_used,
                },
                "terraform_scout": {
                    "summary": state.terraform_scout_summary,
                    "tools_used": state.terraform_scout_tools_used,
                },
                "ops_diagnostics": {
                    "result": state.ops_analyst_result,
                    "tools_used": state.ops_analyst_tools_used,
                },
                "root_cause": state.root_cause,
                "causal_chain": state.causal_chain,
                "blast_radius": {
                    "count": state.graph_context.get("blast_radius_count", 0),
                    "upstream": state.graph_context.get("upstream_services", []),
                    "downstream": state.graph_context.get("downstream_services", []),
                },
                "remediation_steps": state.remediation_steps,
                "rollback_steps": state.rollback_steps,
                "escalation_paths": state.escalation_paths,
                "runbook_references": state.runbook_references,
                "timeline": state.timeline,
                "web_citations": state.web_citations,
                "completed_steps": state.completed_steps,
                "errors": state.errors,
            },
        )
