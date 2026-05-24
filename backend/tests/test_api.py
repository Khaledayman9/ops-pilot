from unittest.mock import AsyncMock, patch

import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ops-pilot"


@pytest.mark.asyncio
async def test_analyze_incident_endpoint(
    mock_classification,
    mock_graph_output,
    mock_root_cause,
    mock_remediation,
):
    from app.schemas.incident import IncidentResponse
    from app.services.incident_service import IncidentService

    mock_response = IncidentResponse(
        session_id="test-session-123",
        classification=mock_classification.model_dump(),
        graph_context=mock_graph_output.model_dump(),
        root_cause=mock_root_cause.primary_cause,
        blast_radius={"count": 4, "upstream": [], "downstream": []},
        remediation_steps=["Scale pods", "Rollback deploy"],
        timeline=mock_root_cause.timeline_reconstruction,
    )

    with patch.object(
        IncidentService,
        "analyze",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/incident/analyze",
                json={"query": "Checkout service is slow after deployment"},
            )

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "root_cause" in data
    assert "remediation_steps" in data
