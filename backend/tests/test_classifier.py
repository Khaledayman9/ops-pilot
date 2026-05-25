import pytest
from unittest.mock import AsyncMock, patch

from app.agents.classifier import ClassifierAgent, ClassificationInput, ClassificationOutput


@pytest.mark.asyncio
async def test_classifier_returns_structured_output(mock_classification):
    agent = ClassifierAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_classification)
        result = await agent.run(
            ClassificationInput(query="Checkout service is slow after deployment")
        )
    assert isinstance(result, ClassificationOutput)
    assert result.service == "checkout-service"
    assert result.severity == "P1"
    assert result.incident_type == "latency"
    assert 0.0 <= result.confidence <= 1.0
    assert result.severity in {"P0", "P1", "P2", "P3"}


@pytest.mark.asyncio
async def test_classifier_inherits_base_agent():
    from app.core.base_agent import BaseAgent

    agent = ClassifierAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_name == "classifier"


@pytest.mark.asyncio
async def test_classifier_loads_prompts():
    agent = ClassifierAgent()
    assert "system" in agent._prompts
    assert "user_template" in agent._prompts
    assert len(agent._prompts["system"]) > 10
