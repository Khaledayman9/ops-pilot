"""
CrewAI-powered incident analysis crew.

Two specialised CrewAI agents work sequentially:
  1. IntelligenceAgent  — searches the web and enriches context.
  2. SynthesisAgent     — synthesises all evidence into a structured verdict.

This crew runs INSIDE the LangGraph orchestrator as an enrichment step
between graph traversal and root cause analysis, giving the RCA agent
richer context than graph data alone.
"""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from app.core import llm
from logger import logger
from .utils import WebSearchTool


class IncidentAnalysisCrew:
    """
    Two-agent CrewAI crew that enriches incident context with external intelligence.

    Usage::

        crew = IncidentAnalysisCrew()
        report = await crew.run(
            service="checkout-service",
            incident_type="latency",
            query="Checkout service is slow after v2.3.1 deployment",
            deployment_version="v2.3.1",
            graph_summary="4 services in blast radius.",
        )
        # report is a str — structured enrichment text for the RCA agent
    """

    def __init__(self) -> None:
        search_tool = WebSearchTool()

        self._intelligence_agent = Agent(
            role="DevOps Intelligence Gatherer",
            goal=(
                "Search the web for known bugs, CVEs, recent changelog entries, "
                "community incident reports, and vendor status page updates "
                "related to the affected service and its dependencies."
            ),
            backstory=(
                "You are an elite SRE researcher who specialises in rapid context "
                "gathering during production incidents. You know that the fastest "
                "path to resolution is finding whether someone else has seen this "
                "failure before. You use DuckDuckGo to surface the most relevant "
                "external intelligence within minutes."
            ),
            tools=[search_tool],
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        self._synthesis_agent = Agent(
            role="Incident Evidence Synthesiser",
            goal=(
                "Take all gathered intelligence and synthesise it into a concise, "
                "structured enrichment report that the Root Cause Analysis agent "
                "can use as supplementary evidence."
            ),
            backstory=(
                "You are a seasoned incident commander who has managed hundreds of "
                "P0 incidents. You excel at filtering noise, identifying signal, and "
                "presenting findings in a clear, actionable format under extreme time "
                "pressure. You never speculate — every claim you make is backed by "
                "a source."
            ),
            tools=[],
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

    async def run(
        self,
        service: str,
        incident_type: str,
        query: str,
        deployment_version: str | None = None,
        graph_summary: str = "",
    ) -> str:
        """
        Execute the crew and return a structured enrichment string.

        The return value is injected into the RootCauseFinderAgent's
        ``web_context`` parameter.
        """
        logger.info(f"[IncidentAnalysisCrew] Running for service={service}")

        search_task = Task(
            description=(
                f"The following production incident has been reported:\n\n"
                f"Query: {query}\n"
                f"Primary service: {service}\n"
                f"Incident type: {incident_type}\n"
                f"Deployment version: {deployment_version or 'unknown'}\n"
                f"Graph summary: {graph_summary}\n\n"
                f"Search for:\n"
                f"1. Known bugs or issues in {service} version {deployment_version or 'latest'}.\n"
                f"2. CVEs or security advisories for {service}.\n"
                f"3. Community posts about {incident_type} incidents in {service}.\n"
                f"4. The {service} changelog for version {deployment_version or 'latest'}.\n"
                f"5. Any vendor status page entries in the last 24 hours.\n\n"
                f"Return a numbered list of your findings with source URLs."
            ),
            agent=self._intelligence_agent,
            expected_output=(
                "A numbered list of relevant findings, each with a source URL, "
                "directly related to the incident."
            ),
        )

        synthesis_task = Task(
            description=(
                "Using the intelligence gathered, produce a structured enrichment "
                "report with the following sections:\n\n"
                "## Known Issues\n"
                "List any confirmed bugs, CVEs, or known failure modes.\n\n"
                "## Deployment Risk\n"
                "Summarise any changelog entries or release notes relevant to "
                f"version {deployment_version or 'latest'} of {service}.\n\n"
                "## Community Signal\n"
                "Note any similar community-reported incidents or Stack Overflow threads.\n\n"
                "## Vendor Status\n"
                "Report any active vendor incidents or recent status-page events.\n\n"
                "Keep the entire report under 400 words. Cite all sources."
            ),
            agent=self._synthesis_agent,
            expected_output=(
                "A structured markdown report with four sections: Known Issues, "
                "Deployment Risk, Community Signal, and Vendor Status."
            ),
            context=[search_task],
        )

        crew = Crew(
            agents=[self._intelligence_agent, self._synthesis_agent],
            tasks=[search_task, synthesis_task],
            process=Process.sequential,
            verbose=False,
        )

        try:
            result = crew.kickoff()
            output: str = str(result)
            logger.info(f"[IncidentAnalysisCrew] Completed, {len(output)} chars")
            return output
        except Exception as exc:
            logger.warning(f"[IncidentAnalysisCrew] Failed: {exc}")
            return f"Web intelligence gathering failed: {exc}"
