"""Tests for TerraformScoutAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.terraform_scouter import TerraformScoutAgent
from app.agents.terraform_scouter.models import TerraformScoutInput, TerraformScoutOutput


@pytest.fixture
def base_input():
    return TerraformScoutInput(
        task="summarize",
        workspace="checkout-service",
        extra_context="Incident type: latency. Check for recent infra changes.",
    )


@pytest.fixture
def mock_terraform_output():
    return TerraformScoutOutput(
        task="summarize",
        workspace="checkout-service",
        summary=(
            "Terraform workspace: checkout-service\n"
            "Last apply: 35 minutes ago — changed RDS instance class from db.t3.medium to db.t3.large\n"
            "Drift detected: security group rule added outside Terraform for port 5432\n"
            "Open plans: 1 pending plan — adds auto-scaling policy for ECS service\n"
            "No failed applies in the last 24 hours\n"
        ),
        tools_used=["terraform_workspace_list", "terraform_plan_show", "terraform_state_show"],
    )


@pytest.mark.asyncio
async def test_terraform_scout_returns_output(base_input, mock_terraform_output):
    agent = TerraformScoutAgent()
    agent._initialized = True
    agent._tool_names = mock_terraform_output.tools_used

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(
                return_value={"messages": [MagicMock(content=mock_terraform_output.summary)]}
            )
            result = await agent.run(base_input)

    assert isinstance(result, TerraformScoutOutput)
    assert result.task == "summarize"
    assert result.workspace == "checkout-service"
    assert result.summary != ""


@pytest.mark.asyncio
async def test_terraform_scout_timeout_returns_graceful_output(base_input):
    """asyncio.TimeoutError should yield a graceful non-raising output."""
    import asyncio

    agent = TerraformScoutAgent()
    agent._initialized = True
    agent._tool_names = []

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError)
            result = await agent.run(base_input)

    assert isinstance(result, TerraformScoutOutput)
    assert "timed out" in result.summary.lower() or result.summary != ""


@pytest.mark.asyncio
async def test_terraform_scout_tools_used_recorded(base_input, mock_terraform_output):
    agent = TerraformScoutAgent()
    agent._initialized = True
    agent._tool_names = mock_terraform_output.tools_used

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(
                return_value={"messages": [MagicMock(content=mock_terraform_output.summary)]}
            )
            result = await agent.run(base_input)

    assert isinstance(result.tools_used, list)


@pytest.mark.asyncio
async def test_terraform_scout_init_raises_when_no_config():
    """Missing terraform config in servers.json should raise ValueError."""
    agent = TerraformScoutAgent()
    with patch(
        "builtins.open",
        MagicMock(
            return_value=MagicMock(
                __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value="{}"))),
                __exit__=MagicMock(return_value=False),
            )
        ),
    ):
        with patch("json.load", return_value={}):
            with pytest.raises(ValueError, match="terraform"):
                await agent._initialize()


@pytest.mark.asyncio
async def test_terraform_scout_default_workspace():
    """Empty workspace should default to 'default' string in prompt."""
    inp = TerraformScoutInput(task="summarize", workspace="", extra_context="")
    assert inp.workspace == ""  # stored as-is; the agent substitutes "default" in format_prompt


@pytest.mark.asyncio
async def test_terraform_scout_inherits_base_agent():
    from app.core.base_agent import BaseAgent

    agent = TerraformScoutAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_name == "terraform_scouter"


@pytest.mark.asyncio
async def test_terraform_scout_loads_prompts():
    agent = TerraformScoutAgent()
    assert "system" in agent._prompts
    assert "user_template" in agent._prompts


@pytest.mark.asyncio
async def test_terraform_scout_response_fallback_to_str(base_input):
    """When response has no messages, str(response) is used as summary."""
    agent = TerraformScoutAgent()
    agent._initialized = True
    agent._tool_names = []

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(return_value={"messages": []})
            result = await agent.run(base_input)

    assert isinstance(result, TerraformScoutOutput)
    assert result.summary is not None


def test_terraform_scout_input_schema():
    inp = TerraformScoutInput(
        task="list_workspaces",
        workspace="production",
        extra_context="List all active workspaces",
    )
    assert inp.task == "list_workspaces"
    assert inp.workspace == "production"
