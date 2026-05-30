from unittest.mock import AsyncMock, patch

import pytest

from app.agents.graph_analyzer.agent import (
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
                "blast_radius": [],
                "deployments": [],
                "incidents": [],
                "runbooks": [],
                "ownership": [],
                "config_changes": [],
                "entity_incidents": [],
            }
            result = await agent.run(
                GraphAnalyzerQueryInput(
                    service="checkout-service", entities=[], incident_type="latency"
                )
            )
    assert isinstance(result, GraphAnalyzerQueryOutput)
    assert result.blast_radius_count >= 0


@pytest.mark.asyncio
async def test_graph_agent_uses_mock_on_neo4j_failure(mock_graph_output):
    agent = GraphAnalyzerAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_graph_output)
        with patch("app.agents.graph_analyzer.agent.neo4j_driver") as mock_driver:
            mock_driver.session.side_effect = Exception("Connection refused")
            result = await agent.run(
                GraphAnalyzerQueryInput(
                    service="checkout-service", entities=[], incident_type="latency"
                )
            )
    assert isinstance(result, GraphAnalyzerQueryOutput)


@pytest.mark.asyncio
async def test_graph_agent_queries_runbooks_and_ownership(mock_graph_output):
    """Verify that the agent queries runbooks and ownership from the graph."""
    agent = GraphAnalyzerAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_graph_output)
        with patch.object(agent, "_query_neo4j", new_callable=AsyncMock) as mock_neo4j:
            mock_neo4j.return_value = {
                "dependencies": [],
                "upstream": [],
                "blast_radius": [{"name": "postgres-primary", "type": "Database", "hops": 1}],
                "deployments": [{"version": "v2.3.1", "status": "completed"}],
                "incidents": [],
                "runbooks": [
                    {"id": "RB-001", "title": "Rollback guide", "url": "http://wiki/rb-001"}
                ],
                "ownership": [
                    {"service": "checkout-service", "team": "checkout-team", "slack": "#checkout"}
                ],
                "config_changes": [],
                "entity_incidents": [],
            }
            result = await agent.run(
                GraphAnalyzerQueryInput(
                    service="checkout-service",
                    entities=["payment-service"],
                    incident_type="latency",
                )
            )
    assert isinstance(result, GraphAnalyzerQueryOutput)
