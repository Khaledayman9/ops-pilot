"""Tests for RootCauseFinderAgent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.root_cause_finder import RootCauseFinderAgent
from app.agents.root_cause_finder.models import (
    CausalFactor,
    RootCauseFinderInput,
    RootCauseFinderOutput,
)


@pytest.fixture
def base_input():
    return RootCauseFinderInput(
        query="Checkout service p99 latency exceeded 3s after deployment v2.3.1 at 10:30 UTC",
        service="checkout-service",
        incident_type="latency",
        severity="P1",
        graph_context={
            "upstream_services": ["api-gateway", "mobile-bff"],
            "downstream_services": ["payment-service", "inventory-service"],
            "blast_radius_count": 4,
            "recent_deployments": [{"version": "v2.3.1", "status": "completed", "age_minutes": 30}],
            "related_incidents": [{"id": "INC-099", "severity": "P2", "age_days": 14}],
            "runbooks": [{"id": "RB-001", "title": "Checkout rollback guide"}],
            "ownership": [{"service": "checkout-service", "team": "checkout-squad"}],
            "affected_services": ["checkout-service"],
        },
        classification={
            "service": "checkout-service",
            "severity": "P1",
            "incident_type": "latency",
            "confidence": 0.92,
        },
    )


@pytest.fixture
def mock_rca_output():
    return RootCauseFinderOutput(
        primary_cause="Memory leak in v2.3.1 connection pool manager causing DB connection exhaustion",
        causal_chain=[
            CausalFactor(
                factor="Deployment v2.3.1 introduced memory leak",
                confidence=0.93,
                evidence="Deployed 30 minutes before latency spike; memory usage climbed steadily",
            ),
            CausalFactor(
                factor="DB connection pool exhausted",
                confidence=0.87,
                evidence="p99 latency spike correlates with pool saturation metrics",
            ),
            CausalFactor(
                factor="Downstream payment-service timeouts",
                confidence=0.78,
                evidence="Payment service error rate rose 2 minutes after checkout spike",
            ),
        ],
        contributing_factors=[
            "High traffic volume during deploy window",
            "No canary deployment gate",
            "Missing connection pool size alert",
        ],
        deployment_correlation=True,
        deployment_version="v2.3.1",
        timeline_reconstruction=[
            "10:30 UTC — Deployment v2.3.1 completed to production",
            "10:45 UTC — Memory usage begins steady climb",
            "11:00 UTC — p99 latency exceeds 2s threshold",
            "11:05 UTC — PagerDuty P1 alert fires",
            "11:07 UTC — Payment service error rate rises",
        ],
        confidence_score=0.88,
        reasoning=(
            "Strong temporal correlation between v2.3.1 deployment and latency onset. "
            "Memory and pool metrics confirm the causal path. "
            "Historical incident INC-099 shows a similar pattern two weeks prior."
        ),
    )


@pytest.mark.asyncio
async def test_root_cause_finder_returns_output(base_input, mock_rca_output):
    agent = RootCauseFinderAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_rca_output)
        result = await agent.run(base_input)

    assert isinstance(result, RootCauseFinderOutput)
    assert result.primary_cause != ""
    assert 0.0 <= result.confidence_score <= 1.0


@pytest.mark.asyncio
async def test_root_cause_finder_causal_chain_structure(base_input, mock_rca_output):
    agent = RootCauseFinderAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_rca_output)
        result = await agent.run(base_input)

    assert len(result.causal_chain) > 0
    for factor in result.causal_chain:
        assert isinstance(factor, CausalFactor)
        assert 0.0 <= factor.confidence <= 1.0
        assert factor.factor != ""
        assert factor.evidence != ""


@pytest.mark.asyncio
async def test_root_cause_finder_deployment_correlation(base_input, mock_rca_output):
    agent = RootCauseFinderAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_rca_output)
        result = await agent.run(base_input)

    assert result.deployment_correlation is True
    assert result.deployment_version == "v2.3.1"


@pytest.mark.asyncio
async def test_root_cause_finder_timeline_reconstruction(base_input, mock_rca_output):
    agent = RootCauseFinderAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_rca_output)
        result = await agent.run(base_input)

    assert len(result.timeline_reconstruction) > 0
    assert all(isinstance(t, str) for t in result.timeline_reconstruction)


@pytest.mark.asyncio
async def test_root_cause_finder_with_web_context(base_input, mock_rca_output):
    agent = RootCauseFinderAgent()
    web_ctx = (
        "Known issue: Redis 7.2 has a memory regression under high write load. "
        "CVE-2024-0001 affects connection pool libraries < 2.1.0."
    )
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_rca_output)
        result = await agent.run(base_input, web_context=web_ctx)

    assert result is not None
    mock_chain.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_root_cause_finder_with_empty_graph_context(mock_rca_output):
    agent = RootCauseFinderAgent()
    inp = RootCauseFinderInput(
        query="Payment service is down",
        service="payment-service",
        incident_type="outage",
        severity="P0",
        graph_context={},
        classification={"service": "payment-service", "severity": "P0", "confidence": 0.95},
    )
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_rca_output)
        result = await agent.run(inp)

    assert isinstance(result, RootCauseFinderOutput)


@pytest.mark.asyncio
async def test_root_cause_finder_inherits_base_agent():
    from app.core.base_agent import BaseAgent

    agent = RootCauseFinderAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_name == "root_cause_finder"


@pytest.mark.asyncio
async def test_root_cause_finder_loads_prompts():
    agent = RootCauseFinderAgent()
    assert "system" in agent._prompts
    assert "user_template" in agent._prompts


@pytest.mark.asyncio
async def test_root_cause_finder_no_deployment_correlation(mock_rca_output):
    """When no deployment is correlated, deployment_version should be None."""
    agent = RootCauseFinderAgent()
    no_deploy_output = RootCauseFinderOutput(
        primary_cause="Cascading failure from upstream API gateway timeout",
        causal_chain=[
            CausalFactor(
                factor="API gateway timeout",
                confidence=0.80,
                evidence="Gateway logs show 30s timeouts",
            )
        ],
        contributing_factors=["Insufficient timeout configuration"],
        deployment_correlation=False,
        deployment_version=None,
        timeline_reconstruction=["14:00 UTC — Gateway timeouts begin", "14:05 UTC — Alert fires"],
        confidence_score=0.75,
        reasoning="No deployment found in the incident window. Root cause is upstream.",
    )
    inp = RootCauseFinderInput(
        query="Services timing out",
        service="api-gateway",
        incident_type="timeout",
        severity="P1",
        graph_context={"recent_deployments": []},
        classification={"service": "api-gateway", "severity": "P1", "confidence": 0.80},
    )
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=no_deploy_output)
        result = await agent.run(inp)

    assert result.deployment_correlation is False
    assert result.deployment_version is None