import pytest

from app.agents import (
    CausalFactor,
    ClassificationOutput,
    EntityExtraction,
    EntityExtractorOutput,
    EscalationPath,
    GraphAnalyzerQueryOutput,
    RemediationStep,
    RemediatorOutput,
    RootCauseFinderOutput,
)


@pytest.fixture
def mock_classification():
    return ClassificationOutput(
        service="checkout-service",
        severity="P1",
        incident_type="latency",
        affected_components=["checkout-service", "payment-service"],
        trigger_event="deployment",
        confidence=0.92,
    )


@pytest.fixture
def mock_search_output():
    return EntityExtractorOutput(
        entities=EntityExtraction(
            services=["checkout-service", "payment-service"],
            deployments=["v2.3.1"],
            metrics=["latency", "error_rate"],
            time_range="last 1 hour",
            error_codes=["500", "503"],
            keywords=["slow"],
        ),
        search_queries=["MATCH (s:Service {name:'checkout-service'})"],
        context_summary="Checkout latency spike after v2.3.1",
    )


@pytest.fixture
def mock_graph_output():
    return GraphAnalyzerQueryOutput(
        affected_services=[],
        dependency_edges=[],
        upstream_services=["api-gateway", "mobile-bff"],
        downstream_services=["payment-service", "inventory-service"],
        blast_radius_count=4,
        recent_deployments=[{"version": "v2.3.1", "status": "completed"}],
        related_incidents=[{"id": "INC-001", "severity": "P1"}],
        graph_summary="4 services in blast radius.",
    )


@pytest.fixture
def mock_root_cause():
    return RootCauseFinderOutput(
        primary_cause="Memory leak in v2.3.1 causing DB connection pool exhaustion",
        causal_chain=[
            CausalFactor(
                factor="Deployment v2.3.1",
                confidence=0.9,
                evidence="Deployed 30min before incident",
            ),
            CausalFactor(
                factor="DB pool exhaustion",
                confidence=0.85,
                evidence="Latency matches pool saturation",
            ),
        ],
        contributing_factors=["High traffic during deploy window"],
        deployment_correlation=True,
        deployment_version="v2.3.1",
        timeline_reconstruction=[
            "10:30 — Deployment v2.3.1 completed",
            "11:00 — p99 latency exceeded 2s",
            "11:05 — PagerDuty alert fired",
        ],
        confidence_score=0.88,
        reasoning="Strong temporal correlation between deployment and latency spike.",
    )


@pytest.fixture
def mock_remediation():
    return RemediatorOutput(
        immediate_actions=[
            RemediationStep(
                order=1,
                action="Scale checkout pods to 10",
                command="kubectl scale deploy/checkout --replicas=10",
                expected_outcome="Reduced per-pod load",
                risk_level="low",
                estimated_minutes=2,
            ),
        ],
        rollback_steps=[
            RemediationStep(
                order=1,
                action="Rollback to v2.3.0",
                command="kubectl rollout undo deploy/checkout",
                expected_outcome="Stable version restored",
                risk_level="medium",
                estimated_minutes=5,
            ),
        ],
        mitigation_steps=[
            RemediationStep(
                order=1,
                action="Enable circuit breaker",
                command=None,
                expected_outcome="Reduced cascading failures",
                risk_level="low",
                estimated_minutes=3,
            ),
        ],
        escalation_paths=[
            EscalationPath(
                team="checkout-team", contact="#checkout-squad", condition="Not resolved in 15min"
            ),
        ],
        runbook_references=["https://wiki.internal/runbooks/checkout-rollback"],
        estimated_resolution_minutes=20,
        post_incident_actions=["Add canary deployment gate"],
        summary="Rollback v2.3.1 and scale pods.",
    )
