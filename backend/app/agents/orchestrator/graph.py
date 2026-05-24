from collections.abc import AsyncGenerator

from app.schemas.stream import StreamEvent
from logger import logger

from ..classifier import ClassificationInput, ClassifierAgent
from ..graph_analyzer import GraphAnalyzerAgent, GraphAnalyzerQueryInput
from ..remediator import RemediatorAgent, RemediatorInput
from ..root_cause_finder import RootCauseFinderAgent, RootCauseFinderInput
from ..searcher import SearcherAgent, SearchInput
from ..web_searcher import WebSearcherAgent, WebSearchInput
from ..crew.incident_crew import IncidentAnalysisCrew
from .models import IncidentState


class IncidentOrchestrator:
    def __init__(self) -> None:
        self._classifier = ClassifierAgent()
        self._searcher = SearcherAgent()
        self._graph = GraphAnalyzerAgent()
        self._web_searcher = WebSearcherAgent()
        self._crew = IncidentAnalysisCrew()
        self._root_cause = RootCauseFinderAgent()
        self._remediator = RemediatorAgent()

    async def run_with_stream(
        self, query: str, session_id: str
    ) -> AsyncGenerator[StreamEvent, None]:
        state = IncidentState(query=query, session_id=session_id)

        # Classify
        yield StreamEvent(
            event="step",
            agent="classifier",
            step="classify",
            status="running",
            data={"message": "Classifying incident…"},
        )
        try:
            out = await self._classifier.run(ClassificationInput(query=query))
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

        # Entity extraction
        yield StreamEvent(
            event="step",
            agent="searcher",
            step="entity_extraction",
            status="running",
            data={"message": "Extracting entities…"},
        )
        try:
            out = await self._searcher.run(
                SearchInput(
                    query=query,
                    service=state.service or "unknown",
                    incident_type=state.incident_type or "unknown",
                )
            )
            state.entities = out.entities.model_dump()
            state.completed_steps.append("entity_extraction")
            yield StreamEvent(
                event="step",
                agent="searcher",
                step="entity_extraction",
                status="complete",
                data=state.entities,
            )
        except Exception as exc:
            logger.error(f"[Orchestrator] Searcher: {exc}")
            state.errors.append(str(exc))
            yield StreamEvent(
                event="step",
                agent="searcher",
                step="entity_extraction",
                status="error",
                data={"error": str(exc)},
            )

        # Graph traversal
        yield StreamEvent(
            event="step",
            agent="graph_analyzer",
            step="graph_traversal",
            status="running",
            data={"message": "Traversing dependency graph…"},
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

        # Web intelligence (WebSearcherAgent)
        yield StreamEvent(
            event="step",
            agent="web_searcher",
            step="web_search",
            status="running",
            data={"message": "Searching web for known issues…"},
        )
        web_context = "No supplementary web intelligence available."
        try:
            web_out = await self._web_searcher.run(
                WebSearchInput(query=f"{state.service} {state.incident_type} incident"),
                service=state.service or "unknown",
                incident_type=state.incident_type or "unknown",
                deployment_version=state.deployment_version,
            )
            web_context = web_out.combined_context
            state.completed_steps.append("web_search")
            yield StreamEvent(
                event="step",
                agent="web_searcher",
                step="web_search",
                status="complete",
                data={
                    "results_count": len(web_out.results),
                    "context": web_context[:400],
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

        # CrewAI enrichment
        yield StreamEvent(
            event="step",
            agent="crew",
            step="crew_enrichment",
            status="running",
            data={"message": "Running CrewAI intelligence crew…"},
        )
        try:
            crew_report = await self._crew.run(
                service=state.service or "unknown",
                incident_type=state.incident_type or "unknown",
                query=query,
                deployment_version=state.deployment_version,
                graph_summary=state.graph_context.get("graph_summary", ""),
            )
            # Append crew report to web context
            web_context = (
                f"{web_context}\n\n=== CrewAI Intelligence Report ===\n{crew_report}"
            )
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

        # Root cause analysis
        yield StreamEvent(
            event="step",
            agent="root_cause_finder",
            step="root_cause_analysis",
            status="running",
            data={"message": "Running root cause analysis…"},
        )
        try:
            out = await self._root_cause.run(
                RootCauseFinderInput(
                    query=query,
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

        # Remediation
        yield StreamEvent(
            event="step",
            agent="remediator",
            step="remediation",
            status="running",
            data={"message": "Generating remediation plan…"},
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

        # Final result
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
                "graph_context": state.graph_context,
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
