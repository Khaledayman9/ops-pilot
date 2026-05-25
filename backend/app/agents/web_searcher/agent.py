from __future__ import annotations

from app.core import BaseAgent, format_prompt

from .models import WebSearchInput, WebSearchOutput
from .utils import search_to_text, web_search


class WebSearcherAgent(BaseAgent):
    """
    Enriches incident context with real-time DuckDuckGo web intelligence.
    Two strategies: Instant Answer API → HTML scrape fallback.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("web_searcher", **kwargs)
        self._chain = self._build_chain(WebSearchOutput)

    async def run(
        self,
        inp: WebSearchInput,
        *,
        service: str = "unknown",
        incident_type: str = "unknown",
        deployment_version: str | None = None,
    ) -> WebSearchOutput:
        self._log(f"Searching for: {inp.query}")

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

        seen: set[str] = set()
        unique = []
        for r in all_results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)

        search_context = search_to_text(unique) if unique else "No results found."
        self._log(f"Found {len(unique)} unique results")

        user_msg = format_prompt(
            self._prompts["user_template"],
            query=inp.query,
            service=service,
            incident_type=incident_type,
            deployment_version=deployment_version or "N/A",
            search_context=search_context,
        )

        result: WebSearchOutput = await self._chain.ainvoke(
            [
                ("system", self._prompts["system"]),
                ("human", user_msg),
            ]
        )
        result.queries_used = queries
        return result
