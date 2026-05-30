"""Tests for ConversationalistAgent."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.conversationalist import ConversationalistAgent
from app.agents.conversationalist.models import (
    ChatTurn,
    ConversationalistInput,
    ConversationalistOutput,
)


@pytest.fixture
def mock_conv_output_incident():
    return ConversationalistOutput(
        natural_response=(
            "## Incident Summary\n\n"
            "The checkout service is experiencing P1 latency due to a memory leak "
            "introduced in deployment v2.3.1, causing DB connection pool exhaustion.\n\n"
            "**Immediate action:** Rollback to v2.3.0 and scale pods to 10."
        ),
        is_incident_relevant=True,
        summary_for_history=(
            "P1 latency on checkout-service traced to v2.3.1 memory leak. "
            "Recommended rollback and pod scale-up."
        ),
    )


@pytest.fixture
def mock_conv_output_offtopic():
    return ConversationalistOutput(
        natural_response=(
            "I'm here to help with incident analysis. "
            "Could you describe a production incident or system issue?"
        ),
        is_incident_relevant=False,
        summary_for_history="User asked an off-topic question. Redirected to incident context.",
    )


@pytest.fixture
def incident_input():
    return ConversationalistInput(
        query="Checkout service is slow after deployment v2.3.1",
        history=[
            ChatTurn(role="user", content="We had an outage last week too."),
            ChatTurn(role="assistant", content="Noted. I'll factor that into the analysis."),
        ],
        incident_structured={
            "service": "checkout-service",
            "severity": "P1",
            "root_cause": "Memory leak in v2.3.1",
            "remediation_steps": ["Rollback to v2.3.0", "Scale pods to 10"],
            "rollback_steps": ["kubectl rollout undo deploy/checkout"],
        },
        web_citations=[
            {"title": "Known Redis memory leak", "url": "https://github.com/redis/redis/issues/1"}
        ],
        is_incident_query=True,
        analysis_context="Service: checkout-service\nSeverity: P1\nRoot cause: Memory leak in v2.3.1",
    )


@pytest.fixture
def offtopic_input():
    return ConversationalistInput(
        query="What is the weather like today?",
        history=[],
        incident_structured=None,
        web_citations=[],
        is_incident_query=False,
        analysis_context="",
    )


@pytest.mark.asyncio
async def test_conversationalist_incident_response(incident_input, mock_conv_output_incident):
    agent = ConversationalistAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_conv_output_incident)
        result = await agent.run(incident_input)

    assert isinstance(result, ConversationalistOutput)
    assert result.is_incident_relevant is True
    assert len(result.natural_response) > 0
    assert len(result.summary_for_history) > 0
    assert len(result.summary_for_history) <= 800  # should stay concise


@pytest.mark.asyncio
async def test_conversationalist_offtopic_response(offtopic_input, mock_conv_output_offtopic):
    agent = ConversationalistAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_conv_output_offtopic)
        result = await agent.run(offtopic_input)

    assert isinstance(result, ConversationalistOutput)
    assert result.is_incident_relevant is False
    assert result.natural_response != ""


@pytest.mark.asyncio
async def test_conversationalist_with_empty_history(mock_conv_output_incident):
    agent = ConversationalistAgent()
    inp = ConversationalistInput(
        query="Database is timing out",
        history=[],
        incident_structured={"service": "db", "severity": "P0", "root_cause": "disk full"},
        web_citations=[],
        is_incident_query=True,
        analysis_context="Service: db\nSeverity: P0",
    )
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_conv_output_incident)
        result = await agent.run(inp)

    assert result is not None
    assert isinstance(result.natural_response, str)


@pytest.mark.asyncio
async def test_conversationalist_with_citations(mock_conv_output_incident):
    agent = ConversationalistAgent()
    inp = ConversationalistInput(
        query="Redis CPU is maxed out",
        history=[],
        incident_structured={"service": "redis", "severity": "P1", "root_cause": "high traffic"},
        web_citations=[
            {"title": "Redis CPU tuning guide", "url": "https://redis.io/docs/cpu"},
            {"title": "Redis maxmemory policy", "url": "https://redis.io/docs/memory"},
        ],
        is_incident_query=True,
        analysis_context="Service: redis\nSeverity: P1",
    )
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_conv_output_incident)
        result = await agent.run(inp)

    assert result is not None


@pytest.mark.asyncio
async def test_conversationalist_inherits_base_agent():
    from app.core.base_agent import BaseAgent

    agent = ConversationalistAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_name == "conversationalist"


@pytest.mark.asyncio
async def test_conversationalist_loads_prompts():
    agent = ConversationalistAgent()
    assert "system" in agent._prompts
    assert "user_template" in agent._prompts
    assert len(agent._prompts["system"]) > 10


@pytest.mark.asyncio
async def test_conversationalist_output_schema_valid(mock_conv_output_incident):
    """Ensure output matches expected Pydantic schema."""
    out = mock_conv_output_incident
    assert hasattr(out, "natural_response")
    assert hasattr(out, "is_incident_relevant")
    assert hasattr(out, "summary_for_history")
    assert isinstance(out.is_incident_relevant, bool)


@pytest.mark.asyncio
async def test_conversationalist_multi_turn_history(mock_conv_output_incident):
    """Agent should accept and process multi-turn history without error."""
    agent = ConversationalistAgent()
    history = [ChatTurn(role="user", content=f"Turn {i} user message") for i in range(10)]
    inp = ConversationalistInput(
        query="Another incident query",
        history=history,
        incident_structured=None,
        web_citations=[],
        is_incident_query=False,
        analysis_context="",
    )
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_conv_output_incident)
        result = await agent.run(inp)

    # Verify ainvoke was called (history was passed through)
    mock_chain.ainvoke.assert_called_once()
    assert result is not None
