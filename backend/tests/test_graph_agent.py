from unittest.mock import AsyncMock, patch

import pytest
from app.agents import (
    GraphAnalyzerAgent,
    GraphAnalyzerQueryInput,
    GraphAnalyzerQueryOutput,
)


@pytest.mark.asyncio
async def test_graph_agent_returns_output(mock_graph_output):
    agent = GraphAnalyzerAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_graph_output)
        with patch.object(agent, "_query_neo4j", new_callable=AsyncMock) as mock_neo4j:
            mock_neo4j.return_value = {
                "dependencies": [],
                "upstream": [],
                "deployments": [],
                "incidents": [],
            }
            result = await agent.run(
                GraphAnalyzerQueryInput(
                    service="checkout-service",
                    entities=["checkout-service"],
                    incident_type="latency",
                )
            )

    assert isinstance(result, GraphAnalyzerQueryOutput)
    assert result.blast_radius_count >= 0
    assert isinstance(result.upstream_services, list)
    assert isinstance(result.downstream_services, list)


@pytest.mark.asyncio
async def test_graph_agent_falls_back_on_neo4j_error(mock_graph_output):
    agent = GraphAnalyzerAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_graph_output)
        with patch("app.agents.graph_agent.agent.neo4j_driver") as mock_driver:
            mock_driver.session.side_effect = Exception("Connection refused")
            result = await agent.run(
                GraphAnalyzerQueryInput(
                    service="checkout-service",
                    entities=[],
                    incident_type="latency",
                )
            )

    assert isinstance(result, GraphAnalyzerQueryOutput)
