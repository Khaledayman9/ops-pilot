"""
Web search tool — DuckDuckGo HTML + Instant Answer API.
Returns structured results: title, snippet, url.
"""

from __future__ import annotations

from app.agents.web_searcher.models import SearchResult

try:
    import httpx
    from bs4 import BeautifulSoup

    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def web_search(
    query: str,
    max_results: int = 5,
    timeout: int = 10,
) -> list[SearchResult]:
    """
    Real DuckDuckGo search — tries the Instant Answer JSON API first,
    then falls back to the HTML endpoint scrape.

    Args:
        query:       Search query string.
        max_results: Maximum number of results to return.
        timeout:     HTTP timeout in seconds.

    Returns:
        List of SearchResult dataclasses, possibly empty if both
        strategies fail or if httpx/bs4 are not installed.
    """
    if not _AVAILABLE:
        return []

    results: list[SearchResult] = []

    try:
        params = {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1",
        }
        headers = {"User-Agent": "Mozilla/5.0 ops-pilot/1.0"}
        with httpx.Client(
            timeout=timeout, follow_redirects=True, headers=headers
        ) as client:
            r = client.get("https://api.duckduckgo.com/", params=params)
            data = r.json()

        abstract = data.get("AbstractText", "").strip()
        abstract_url = data.get("AbstractURL", "")
        abstract_src = data.get("AbstractSource", "")
        if abstract:
            results.append(
                SearchResult(
                    title=abstract_src or query,
                    snippet=abstract,
                    url=abstract_url,
                )
            )

        for topic in data.get("RelatedTopics", [])[:max_results]:
            text = topic.get("Text", "").strip()
            first_url = topic.get("FirstURL", "")
            if text and len(text) > 20:
                results.append(
                    SearchResult(
                        title=(
                            first_url.split("/")[-1].replace("_", " ")
                            if first_url
                            else query
                        ),
                        snippet=text,
                        url=first_url,
                    )
                )

        infobox = data.get("Infobox", {})
        if isinstance(infobox, dict):
            for entry in infobox.get("content", []):
                label = entry.get("label", "")
                val = entry.get("value", "")
                if label and val:
                    results.append(
                        SearchResult(
                            title=label,
                            snippet=f"{label}: {val}",
                            url=abstract_url,
                        )
                    )
    except Exception:
        pass

    if not results:
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                ),
                "Accept": "text/html",
            }
            with httpx.Client(
                timeout=timeout, follow_redirects=True, headers=headers
            ) as client:
                r = client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query},
                )
            soup = BeautifulSoup(r.text, "html.parser")
            for div in soup.select(".result")[:max_results]:
                title_el = div.select_one(".result__title")
                snippet_el = div.select_one(".result__snippet")
                url_el = div.select_one(".result__url")
                title = title_el.get_text(strip=True) if title_el else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                url = url_el.get_text(strip=True) if url_el else ""
                if title and snippet:
                    results.append(SearchResult(title=title, snippet=snippet, url=url))
        except Exception:
            pass

    return results[:max_results]


def search_to_text(results: list[SearchResult]) -> str:
    """Flatten results into a single string for LLM ingestion."""
    return "\n".join(f"- {r.title}: {r.snippet}" for r in results)
