"""Tests for RemediatorAgent."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.remediator import RemediatorAgent
from app.agents.remediator.models import (
    EscalationPath,
    RemediationStep,
    RemediatorInput,
    RemediatorOutput,
)


@pytest.fixture
def base_input():
    return RemediatorInput(
        service="checkout-service",
        severity="P1",
        primary_cause="Memory leak in v2.3.1 causing DB connection pool exhaustion",
        causal_chain=[
            {"factor": "Deployment v2.3.1", "confidence": 0.93, "evidence": "30min correlation"},
            {"factor": "DB pool exhaustion", "confidence": 0.87, "evidence": "Pool saturation"},
        ],
        blast_radius={
            "blast_radius_count": 4,
            "upstream_services": ["api-gateway"],
            "downstream_services": ["payment-service", "inventory-service"],
        },
        deployment_correlation=True,
        deployment_version="v2.3.1",
    )


@pytest.fixture
def mock_remediation_output():
    return RemediatorOutput(
        immediate_actions=[
            RemediationStep(
                order=1,
                action="Scale checkout pods to 10 replicas",
                command="kubectl scale deploy/checkout --replicas=10 -n production",
                expected_outcome="Reduced per-pod memory pressure within 2 minutes",
                risk_level="low",
                estimated_minutes=2,
            ),
            RemediationStep(
                order=2,
                action="Rollback checkout-service to v2.3.0",
                command="kubectl rollout undo deploy/checkout -n production",
                expected_outcome="Stable version restored, memory leak eliminated",
                risk_level="medium",
                estimated_minutes=5,
            ),
        ],
        rollback_steps=[
            RemediationStep(
                order=1,
                action="Verify rollback completed successfully",
                command="kubectl rollout status deploy/checkout -n production",
                expected_outcome="All pods running v2.3.0",
                risk_level="low",
                estimated_minutes=3,
            ),
        ],
        mitigation_steps=[
            RemediationStep(
                order=1,
                action="Enable circuit breaker for payment-service dependency",
                command=None,
                expected_outcome="Prevent cascading failures to downstream services",
                risk_level="low",
                estimated_minutes=3,
            ),
        ],
        escalation_paths=[
            EscalationPath(
                team="checkout-squad",
                contact="#checkout-squad on Slack",
                condition="Not resolved within 15 minutes",
            ),
            EscalationPath(
                team="platform-sre",
                contact="#platform-sre on Slack",
                condition="Blast radius expands beyond checkout and payment",
            ),
        ],
        runbook_references=[
            "https://wiki.internal/runbooks/checkout-rollback",
            "https://wiki.internal/runbooks/db-pool-exhaustion",
        ],
        estimated_resolution_minutes=20,
        post_incident_actions=[
            "Add canary deployment gate with memory regression test",
            "Set DB connection pool exhaustion alert at 80% utilisation",
            "Conduct post-mortem within 48 hours",
        ],
        summary=(
            "Rollback v2.3.1 and scale pods immediately. "
            "Enable circuit breaker. Escalate to checkout-squad if not resolved in 15 min."
        ),
    )


@pytest.mark.asyncio
async def test_remediator_returns_output(base_input, mock_remediation_output):
    agent = RemediatorAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_remediation_output)
        result = await agent.run(base_input)

    assert isinstance(result, RemediatorOutput)
    assert len(result.immediate_actions) > 0
    assert len(result.rollback_steps) > 0


@pytest.mark.asyncio
async def test_remediator_immediate_actions_structure(base_input, mock_remediation_output):
    agent = RemediatorAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_remediation_output)
        result = await agent.run(base_input)

    for step in result.immediate_actions:
        assert isinstance(step, RemediationStep)
        assert step.order >= 1
        assert step.action != ""
        assert step.risk_level in {"low", "medium", "high"}
        assert step.estimated_minutes > 0


@pytest.mark.asyncio
async def test_remediator_escalation_paths(base_input, mock_remediation_output):
    agent = RemediatorAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_remediation_output)
        result = await agent.run(base_input)

    assert len(result.escalation_paths) > 0
    for path in result.escalation_paths:
        assert isinstance(path, EscalationPath)
        assert path.team != ""
        assert path.contact != ""
        assert path.condition != ""


@pytest.mark.asyncio
async def test_remediator_runbook_references(base_input, mock_remediation_output):
    agent = RemediatorAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_remediation_output)
        result = await agent.run(base_input)

    assert len(result.runbook_references) > 0
    assert all(isinstance(ref, str) for ref in result.runbook_references)


@pytest.mark.asyncio
async def test_remediator_estimated_resolution(base_input, mock_remediation_output):
    agent = RemediatorAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_remediation_output)
        result = await agent.run(base_input)

    assert result.estimated_resolution_minutes > 0


@pytest.mark.asyncio
async def test_remediator_post_incident_actions(base_input, mock_remediation_output):
    agent = RemediatorAgent()
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_remediation_output)
        result = await agent.run(base_input)

    assert len(result.post_incident_actions) > 0


@pytest.mark.asyncio
async def test_remediator_without_deployment_correlation(mock_remediation_output):
    """Remediator should handle cases where no deployment is correlated."""
    agent = RemediatorAgent()
    inp = RemediatorInput(
        service="redis",
        severity="P0",
        primary_cause="OOM kill due to maxmemory misconfiguration",
        causal_chain=[],
        blast_radius={"blast_radius_count": 2, "upstream_services": [], "downstream_services": []},
        deployment_correlation=False,
        deployment_version=None,
    )
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_remediation_output)
        result = await agent.run(inp)

    assert isinstance(result, RemediatorOutput)


@pytest.mark.asyncio
async def test_remediator_inherits_base_agent():
    from app.core.base_agent import BaseAgent

    agent = RemediatorAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_name == "remediator"


@pytest.mark.asyncio
async def test_remediator_loads_prompts():
    agent = RemediatorAgent()
    assert "system" in agent._prompts
    assert "user_template" in agent._prompts


@pytest.mark.asyncio
async def test_remediator_p0_severity(mock_remediation_output):
    """P0 severity input should be accepted without errors."""
    agent = RemediatorAgent()
    inp = RemediatorInput(
        service="payment-service",
        severity="P0",
        primary_cause="Total service outage due to database failover failure",
        causal_chain=[
            {"factor": "Primary DB node failure", "confidence": 0.98, "evidence": "DB logs"}
        ],
        blast_radius={"blast_radius_count": 12, "upstream_services": [], "downstream_services": []},
        deployment_correlation=False,
        deployment_version=None,
    )
    with patch.object(agent, "_chain") as mock_chain:
        mock_chain.ainvoke = AsyncMock(return_value=mock_remediation_output)
        result = await agent.run(inp)

    assert isinstance(result, RemediatorOutput)
    mock_chain.ainvoke.assert_called_once()
