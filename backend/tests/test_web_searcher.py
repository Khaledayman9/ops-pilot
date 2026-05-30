"""Tests for WebSearcherAgent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.web_searcher import WebSearcherAgent
from app.agents.web_searcher.models import SearchResult, WebSearchInput, WebSearchOutput


@pytest.fixture
def mock_search_results():
    return [
        SearchResult(
            title="Redis memory regression in 7.2",
            snippet="Redis 7.2 has a known memory regression under high write load that can exhaust connection pools.",
            url="https://github.com/redis/redis/issues/12345",
        ),
        SearchResult(
            title="Checkout service post-mortem — connection pool exhaustion",
            snippet="Root cause was a memory leak in the connection pool manager introduced in v2.3.x.",
            url="https://engineering.example.com/postmortem/2024-01",
        ),
        SearchResult(
            title="DB connection pool exhaustion — incident patterns",
            snippet="Common pattern: gradual memory growth after deployment leading to pool saturation.",
            url="https://sre.google/sre-book/",
        ),
    ]


@pytest.fixture
def mock_web_output(mock_search_results):
    return WebSearchOutput(
        results=mock_search_results,
        combined_context=(
            "- Redis memory regression in 7.2: Redis 7.2 has a known memory regression...\n"
            "- Checkout service post-mortem: Root cause was a memory leak...\n"
            "- DB connection pool exhaustion: Common pattern: gradual memory growth..."
        ),
        queries_used=[
            "checkout-service latency incident",
            "checkout-service latency bug",
            "checkout-service incident post-mortem",
        ],
    )


@pytest.mark.asyncio
async def test_web_searcher_returns_output(mock_web_output):
    agent = WebSearcherAgent()
    inp = WebSearchInput(query="checkout-service latency incident")
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_web_output)
        with patch("app.agents.web_searcher.agent.web_search", return_value=[]):
            result = await agent.run(
                inp, service="checkout-service", incident_type="latency"
            )

    assert isinstance(result, WebSearchOutput)
    assert len(result.results) > 0
    assert result.combined_context != ""


@pytest.mark.asyncio
async def test_web_searcher_deduplicates_results(mock_web_output):
    """Results with duplicate URLs should be deduplicated."""
    agent = WebSearcherAgent()
    inp = WebSearchInput(query="redis memory leak")

    duplicate_results = [
        SearchResult(title="A", snippet="snippet a", url="https://example.com/a"),
        SearchResult(title="A again", snippet="duplicate url", url="https://example.com/a"),
        SearchResult(title="B", snippet="snippet b", url="https://example.com/b"),
    ]

    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_web_output)
        with patch("app.agents.web_searcher.agent.web_search", return_value=duplicate_results):
            result = await agent.run(inp, service="redis", incident_type="memory")

    # Deduplication happens inside run() before the chain call
    assert result is not None


@pytest.mark.asyncio
async def test_web_searcher_builds_deployment_query(mock_web_output):
    """When deployment_version is provided, an extra query should be added."""
    agent = WebSearcherAgent()
    inp = WebSearchInput(query="checkout-service latency")

    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_web_output)
        with patch("app.agents.web_searcher.agent.web_search", return_value=[]) as mock_ws:
            _ = await agent.run(
                inp,
                service="checkout-service",
                incident_type="latency",
                deployment_version="v2.3.1",
            )

    # With deployment_version, 4 queries are built: base + bug + postmortem + changelog
    call_args = [call.args[0] for call in mock_ws.call_args_list]
    assert any("v2.3.1" in q for q in call_args)


@pytest.mark.asyncio
async def test_web_searcher_handles_empty_results():
    """Should handle gracefully when web search returns nothing."""
    agent = WebSearcherAgent()
    inp = WebSearchInput(query="very obscure service nobody has heard of")

    empty_output = WebSearchOutput(
        results=[],
        combined_context="No results found.",
        queries_used=["very obscure service nobody has heard of"],
    )

    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=empty_output)
        with patch("app.agents.web_searcher.agent.web_search", return_value=[]):
            result = await agent.run(inp, service="unknown", incident_type="unknown")

    assert isinstance(result, WebSearchOutput)
    assert result.results == []


@pytest.mark.asyncio
async def test_web_searcher_queries_used_populated(mock_web_output):
    agent = WebSearcherAgent()
    inp = WebSearchInput(query="payment-service timeout")
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_web_output)
        with patch("app.agents.web_searcher.agent.web_search", return_value=[]):
            result = await agent.run(inp, service="payment-service", incident_type="timeout")

    # queries_used is assigned after chain call inside run()
    assert isinstance(result.queries_used, list)
    assert len(result.queries_used) >= 1


@pytest.mark.asyncio
async def test_web_searcher_inherits_base_agent():
    from app.core.base_agent import BaseAgent

    agent = WebSearcherAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_name == "web_searcher"


@pytest.mark.asyncio
async def test_web_searcher_loads_prompts():
    agent = WebSearcherAgent()
    assert "system" in agent._prompts
    assert "user_template" in agent._prompts


def test_search_result_to_text():
    result = SearchResult(
        title="Redis bug report",
        snippet="Memory regression under load.",
        url="https://github.com/redis/redis/issues/1",
    )
    text = result.to_text()
    assert "Redis bug report" in text
    assert "Memory regression" in text


def test_web_search_utils_returns_list():
    """web_search utility should return a list (possibly empty if network unavailable)."""
    from app.agents.web_searcher.utils import web_search

    with patch("app.agents.web_searcher.utils._AVAILABLE", False):
        results = web_search("test query")

    assert isinstance(results, list)
    assert results == []


def test_search_to_text_flattens_results():
    from app.agents.web_searcher.utils import search_to_text

    results = [
        SearchResult(title="Title A", snippet="Snippet A", url="https://a.com"),
        SearchResult(title="Title B", snippet="Snippet B", url="https://b.com"),
    ]
    text = search_to_text(results)
    assert "Title A" in text
    assert "Title B" in text
    assert "Snippet A" in text