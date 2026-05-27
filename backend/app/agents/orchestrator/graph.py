"""
LangGraph-style incident orchestrator.

Pipeline (9 steps):
  1. ClassifierAgent    — classify service, severity, type
  2. DocumentPreprocessorAgent — Preprocess input documents to Markdown format
  3. EntityExtractorAgent — extract entities
  4. RepoScoutAgent     — GitHub repo intelligence (branches, issues, PRs)
  5. GraphAnalyzerAgent — deep Neo4j traversal
  6. WebSearcherAgent   — DuckDuckGo web intelligence
  7. OpsAnalystAgent    — stack-trace / error-rate / health diagnostics
  8. IncidentAnalysisCrew — CrewAI 2-agent enrichment
  9. RootCauseFinderAgent — structured RCA
  10. RemediatorAgent    — ordered remediation plan
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.schemas.stream import StreamEvent
from logger import logger

from ..classifier import ClassificationInput, ClassifierAgent
from ..crew.incident_crew import IncidentAnalysisCrew
from ..entity_extractor import EntityExtractorAgent, EntityExtractorInput
from ..graph_analyzer import GraphAnalyzerAgent, GraphAnalyzerQueryInput
from ..ops_analyst import AnalysisTask, OpsAnalystAgent, OpsAnalystInput
from ..remediator import RemediatorAgent, RemediatorInput
from ..repo_scouter import RepoScoutAgent, RepoScoutInput
from ..root_cause_finder import RootCauseFinderAgent, RootCauseFinderInput
from ..web_searcher import WebSearcherAgent, WebSearchInput
from .models import IncidentState


class IncidentOrchestrator:
    def __init__(self) -> None:
        self._classifier = ClassifierAgent()
        self._extractor = EntityExtractorAgent()
        self._repo_scout = RepoScoutAgent()
        self._graph = GraphAnalyzerAgent()
        self._web_searcher = WebSearcherAgent()
        self._ops_analyst = OpsAnalystAgent()
        self._crew = IncidentAnalysisCrew()
        self._root_cause = RootCauseFinderAgent()
        self._remediator = RemediatorAgent()

    async def run_with_stream(
        self,
        query: str,
        session_id: str,
        document_context: str = "",
    ) -> AsyncGenerator[StreamEvent, None]:
        state = IncidentState(query=query, session_id=session_id)
        state.document_context = document_context or ""
        state.document_context_chars = len(state.document_context)

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
            data={"message": "Starting orchestrator turn"},
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
                    "characters": state.document_context_chars,
                },
            )

        yield StreamEvent(
            event="step",
            agent="classifier",
            step="classify",
            status="running",
            data={"message": "Classifying incident"},
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
                data=state.classification,
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

        yield StreamEvent(
            event="step",
            agent="entity_extractor",
            step="entity_extraction",
            status="running",
            data={"message": "Extracting entities"},
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
                data=state.entities,
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

        yield StreamEvent(
            event="step",
            agent="repo_scout",
            step="repo_scouting",
            status="running",
            data={"message": "Scouting GitHub repository for recent activity"},
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
                data={"summary": scout_out.summary[:500], "tools_used": scout_out.tools_used},
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

        yield StreamEvent(
            event="step",
            agent="graph_analyzer",
            step="graph_traversal",
            status="running",
            data={"message": "Running Neo4j graph traversal"},
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
                data=state.graph_context,
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

        yield StreamEvent(
            event="step",
            agent="web_searcher",
            step="web_search",
            status="running",
            data={"message": "Searching web for known issues"},
        )
        web_context = "No supplementary web intelligence available."
        if state.document_context:
            web_context = (
                f"{web_context}\n\n=== Uploaded Document Evidence ===\n{state.document_context}"
            )

        try:
            web_out = await self._web_searcher.run(
                WebSearchInput(query=f"{state.service} {state.incident_type} incident"),
                service=state.service or "unknown",
                incident_type=state.incident_type or "unknown",
                deployment_version=state.deployment_version,
            )
            web_context = f"{web_out.combined_context}\n\n{web_context}"
            state.completed_steps.append("web_search")
            yield StreamEvent(
                event="step",
                agent="web_searcher",
                step="web_search",
                status="complete",
                data={"results_count": len(web_out.results), "context": web_context[:400]},
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

        yield StreamEvent(
            event="step",
            agent="ops_analyst",
            step="ops_diagnostics",
            status="running",
            data={"message": "Running operational diagnostics"},
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
                data={"result": analyst_out.result[:500], "tools_used": analyst_out.tools_used},
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

        yield StreamEvent(
            event="step",
            agent="crew",
            step="crew_enrichment",
            status="running",
            data={"message": "Running CrewAI intelligence crew"},
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
                data={"report_length": len(crew_report)},
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

        yield StreamEvent(
            event="step",
            agent="root_cause_finder",
            step="root_cause_analysis",
            status="running",
            data={"message": "Running root cause analysis"},
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
                data=out.model_dump(),
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
            data={"message": "Generating remediation plan"},
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
                data=out.model_dump(),
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
            event="result",
            agent="orchestrator",
            step="complete",
            status="complete",
            data={
                "session_id": state.session_id,
                "service": state.service,
                "severity": state.severity,
                "classification": state.classification,
                "document_context_chars": state.document_context_chars,
                "graph_context": state.graph_context,
                "repo_scout": {
                    "summary": state.repo_scout_summary,
                    "tools_used": state.repo_scout_tools_used,
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
                "completed_steps": state.completed_steps,
                "errors": state.errors,
            },
        )
