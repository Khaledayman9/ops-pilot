from unittest.mock import AsyncMock, patch

import pytest
from app.agents import ClassificationInput, ClassificationOutput, ClassifierAgent


@pytest.mark.asyncio
async def test_classifier_runs(mock_classification):
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
    assert result.confidence > 0.0


@pytest.mark.asyncio
async def test_classifier_structured_fields(mock_classification):
    agent = ClassifierAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_classification)
        result = await agent.run(
            ClassificationInput(query="Database errors on payment service")
        )

    assert hasattr(result, "service")
    assert hasattr(result, "severity")
    assert hasattr(result, "incident_type")
    assert hasattr(result, "affected_components")
    assert hasattr(result, "confidence")
    assert result.severity in {"P0", "P1", "P2", "P3"}
