"""Tests for RepoScoutAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.repo_scouter import RepoScoutAgent
from app.agents.repo_scouter.models import RepoScoutInput, RepoScoutOutput, RepoSummary


@pytest.fixture
def base_input():
    return RepoScoutInput(
        owner="my-org",
        repo="checkout-service",
        task="summarize",
        extra_context="Incident type: latency. Focus on recent commits and PRs.",
    )


@pytest.fixture
def mock_scout_output():
    return RepoScoutOutput(
        owner="my-org",
        repo="checkout-service",
        task="summarize",
        summary=(
            "Recent activity on my-org/checkout-service:\n"
            "- v2.3.1 deployed 30 minutes ago (commit: abc1234) — connection pool refactor\n"
            "- 2 open PRs: 'Fix memory leak in pool manager' (draft), 'Add connection timeout'\n"
            "- CI: 1 failing check on main — integration tests (started after v2.3.1 merge)\n"
            "- No open issues matching latency keywords in last 7 days\n"
        ),
        repo_info=RepoSummary(
            full_name="my-org/checkout-service",
            default_branch="main",
            open_issues=3,
            stars=42,
            language="Python",
        ),
        tools_used=["get_repository", "list_commits", "list_pull_requests", "list_check_runs"],
    )


@pytest.mark.asyncio
async def test_repo_scout_returns_output(base_input, mock_scout_output):
    agent = RepoScoutAgent()
    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(
                return_value={"messages": [MagicMock(content=mock_scout_output.summary)]}
            )
            agent._initialized = True
            agent._tool_names = mock_scout_output.tools_used
            result = await agent.run(base_input)

    assert isinstance(result, RepoScoutOutput)
    assert result.owner == "my-org"
    assert result.repo == "checkout-service"
    assert result.summary != ""


@pytest.mark.asyncio
async def test_repo_scout_timeout_returns_graceful_output(base_input):
    """On asyncio.TimeoutError the agent should return a graceful output, not raise."""
    import asyncio

    agent = RepoScoutAgent()
    agent._initialized = True
    agent._tool_names = ["get_repository"]

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError)
            result = await agent.run(base_input)

    assert isinstance(result, RepoScoutOutput)
    assert "timed out" in result.summary.lower() or result.summary != ""


@pytest.mark.asyncio
async def test_repo_scout_initialization_failure_raises():
    """If MCP tools cannot be loaded, _initialize should raise."""
    agent = RepoScoutAgent()
    with patch.object(agent, "_load_github_tools", new_callable=AsyncMock, side_effect=RuntimeError("No tools")):
        with pytest.raises(RuntimeError, match="No tools"):
            await agent._initialize()


@pytest.mark.asyncio
async def test_repo_scout_inherits_base_agent():
    from app.core.base_agent import BaseAgent

    agent = RepoScoutAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_name == "repo_scouter"


@pytest.mark.asyncio
async def test_repo_scout_loads_prompts():
    agent = RepoScoutAgent()
    assert "system" in agent._prompts
    assert "user_template" in agent._prompts


@pytest.mark.asyncio
async def test_repo_scout_mcp_config_missing(base_input):
    """Missing servers.json should raise FileNotFoundError during init."""
    agent = RepoScoutAgent()
    with patch("app.agents.repo_scouter.agent._MCP_CONFIG_PATH") as mock_path:
        mock_path.exists.return_value = False
        with pytest.raises(FileNotFoundError):
            await agent._load_github_tools()


@pytest.mark.asyncio
async def test_repo_scout_empty_messages_fallback(base_input):
    """When agent response has no messages, output field is used as fallback."""
    agent = RepoScoutAgent()
    agent._initialized = True
    agent._tool_names = []

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(
                return_value={"messages": [], "output": "Fallback output text"}
            )
            result = await agent.run(base_input)

    assert "Fallback output text" in result.summary


@pytest.mark.asyncio
async def test_repo_scout_input_schema():
    """RepoScoutInput should accept all fields correctly."""
    inp = RepoScoutInput(
        owner="acme",
        repo="api-gateway",
        task="list_branches",
        extra_context="Look for recent branch activity",
    )
    assert inp.owner == "acme"
    assert inp.repo == "api-gateway"
    assert inp.task == "list_branches"


def test_repo_summary_defaults():
    """RepoSummary should have safe defaults when fields are missing."""
    summary = RepoSummary()
    assert summary.full_name == ""
    assert summary.open_issues == 0
    assert summary.stars == 0
    assert summary.language is None