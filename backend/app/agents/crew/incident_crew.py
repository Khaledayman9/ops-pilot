"""
CrewAI-powered incident analysis crew.

Two agents run sequentially:
  1. IntelligenceAgent  — searches the web for known issues, CVEs, changelogs.
  2. SynthesisAgent     — synthesises evidence into a structured enrichment report.
"""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from settings import settings
from logger import logger

from .utils import WebSearchTool


def _crewai_llm_string() -> str:
    """
    Return a CrewAI-compatible LLM identifier string.

    CrewAI's Agent.llm must be a plain string (e.g. 'openai/gpt-4o',
    'anthropic/claude-3-5-sonnet-20241022') or a CrewAI BaseLLM instance.
    LangChain BaseChatModel objects are NOT accepted.
    """
    provider = settings.LLM_PROVIDER.lower()
    model = settings.LLM_MODEL

    if provider == "openai":
        return f"openai/{model}"
    if provider == "anthropic":
        return f"anthropic/{model or settings.ANTHROPIC_MODEL}"
    if provider == "google":
        return f"google/{model or settings.GOOGLE_MODEL}"

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{provider}' for CrewAI. "
        "Choose one of: openai, anthropic, google."
    )


class IncidentAnalysisCrew:
    def __init__(self) -> None:
        search_tool = WebSearchTool()
        crewai_llm = _crewai_llm_string()

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
            llm=crewai_llm,
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
            llm=crewai_llm,
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
        logger.info(f"[IncidentAnalysisCrew] Running for service={service}")

        search_task = Task(
            description=(
                f"Production incident reported:\n\n"
                f"Query: {query}\n"
                f"Primary service: {service}\n"
                f"Incident type: {incident_type}\n"
                f"Deployment version: {deployment_version or 'unknown'}\n"
                f"Graph summary: {graph_summary}\n\n"
                f"Search for:\n"
                f"1. Known bugs in {service} version {deployment_version or 'latest'}.\n"
                f"2. CVEs or security advisories for {service}.\n"
                f"3. Community posts about {incident_type} incidents in {service}.\n"
                f"4. The {service} changelog for version {deployment_version or 'latest'}.\n"
                f"5. Any vendor status page entries in the last 24 hours.\n\n"
                f"Return a numbered list of findings with source URLs."
            ),
            agent=self._intelligence_agent,
            expected_output=("A numbered list of relevant findings, each with a source URL."),
        )

        synthesis_task = Task(
            description=(
                "Using the gathered intelligence, produce a structured enrichment "
                "report with sections:\n\n"
                "## Known Issues\n"
                "## Deployment Risk\n"
                "## Community Signal\n"
                "## Vendor Status\n\n"
                "Keep under 400 words. Cite all sources."
            ),
            agent=self._synthesis_agent,
            expected_output=("A structured markdown report with four sections."),
            context=[search_task],
        )

        crew = Crew(
            agents=[self._intelligence_agent, self._synthesis_agent],
            tasks=[search_task, synthesis_task],
            process=Process.sequential,
            verbose=False,
        )

        try:
            result = await crew.kickoff_async()
            output: str = str(result)
            logger.info(f"[IncidentAnalysisCrew] Completed, {len(output)} chars")
            return output
        except Exception as exc:
            logger.warning(f"[IncidentAnalysisCrew] Failed: {exc}")
            return f"Web intelligence gathering failed: {exc}"
