"""
WebSearcherAgent — enriches incident context with real-time web intelligence.

Uses DuckDuckGo (no API key required) via two strategies:
  1. Instant Answer JSON API
  2. HTML endpoint scrape fallback

The raw results are then synthesised by the LLM into structured supplementary
context consumed by the RootCauseFinderAgent.
"""

from __future__ import annotations

from .models import WebSearchInput, WebSearchOutput
from .utils import search_to_text, web_search
from app.core import llm, format_prompt, load_prompt
from logger import logger


class WebSearcherAgent:
    def __init__(self) -> None:
        self._llm = llm.with_structured_output(WebSearchOutput)
        self._prompts = load_prompt("web_searcher")

    async def run(
        self,
        inp: WebSearchInput,
        *,
        service: str = "unknown",
        incident_type: str = "unknown",
        deployment_version: str | None = None,
    ) -> WebSearchOutput:
        logger.info(f"[WebSearcherAgent] Searching for: {inp.query}")

        # Build targeted queries
        queries = [
            inp.query,
            f"{service} {incident_type} bug",
            f"{service} incident post-mortem",
        ]
        if deployment_version:
            queries.append(f"{service} {deployment_version} changelog")

        all_results = []
        for q in queries[: inp.max_results]:
            all_results.extend(web_search(q, max_results=3))

        # Deduplicate by url
        seen: set[str] = set()
        unique = []
        for r in all_results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        search_context = search_to_text(unique) if unique else "No results found."
        logger.info(f"[WebSearcherAgent] Found {len(unique)} unique results")

        user_msg = format_prompt(
            self._prompts["user_template"],
            query=inp.query,
            service=service,
            incident_type=incident_type,
            deployment_version=deployment_version or "N/A",
            search_context=search_context,
        )

        result: WebSearchOutput = await self._llm.ainvoke(
            [
                ("system", self._prompts["system"]),
                ("human", user_msg),
            ]
        )
        result.queries_used = queries
        return result
