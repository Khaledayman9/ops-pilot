from crewai.tools import BaseTool
from app.agents.web_searcher import SearchResult, web_search


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web using DuckDuckGo. "
        "Use this to find known bugs, CVEs, changelogs, and post-mortems "
        "related to a service or technology. "
        "Input: a search query string. Returns: titles and snippets."
    )

    def _run(self, query: str, max_results: int = 5) -> str:  # type: ignore[override]
        results: list[SearchResult] = web_search(query, max_results=max_results)
        if not results:
            return "No results found."
        return "\n".join(f"[{r.url}] {r.title}: {r.snippet}" for r in results)
