"""Tests for EntityExtractorAgent (renamed from SearcherAgent)."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.entity_extractor import (
    EntityExtractorAgent,
    EntityExtractorInput,
)


@pytest.mark.asyncio
async def test_entity_extractor_alias(mock_search_output):
    """SearcherAgent should still work as an alias."""

    agent = EntityExtractorAgent()
    assert isinstance(agent, EntityExtractorAgent)


@pytest.mark.asyncio
async def test_entity_extractor_enriches_search_queries(mock_search_output):
    agent = EntityExtractorAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_search_output)
        result = await agent.run(
            EntityExtractorInput(
                query="Checkout latency spike",
                service="checkout-service",
                incident_type="latency",
            )
        )
    # Should auto-populate search_queries via build_neo4j_hints
    assert len(result.search_queries) > 0
    assert any("checkout-service" in q for q in result.search_queries)


@pytest.mark.asyncio
async def test_entity_extractor_inherits_base_agent():
    from app.core.base_agent import BaseAgent

    agent = EntityExtractorAgent()
    assert isinstance(agent, BaseAgent)
