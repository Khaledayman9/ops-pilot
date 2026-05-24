from unittest.mock import AsyncMock, patch

import pytest
from app.agents.orchestrator.graph import IncidentOrchestrator
from app.schemas.stream import StreamEvent


@pytest.mark.asyncio
async def test_orchestrator_streams_all_steps(
    mock_classification,
    mock_search_output,
    mock_graph_output,
    mock_root_cause,
    mock_remediation,
):
    orchestrator = IncidentOrchestrator()

    with (
        patch.object(
            orchestrator._classifier,
            "run",
            new_callable=AsyncMock,
            return_value=mock_classification,
        ),
        patch.object(
            orchestrator._searcher,
            "run",
            new_callable=AsyncMock,
            return_value=mock_search_output,
        ),
        patch.object(
            orchestrator._graph_agent,
            "run",
            new_callable=AsyncMock,
            return_value=mock_graph_output,
        ),
        patch.object(
            orchestrator._root_cause,
            "run",
            new_callable=AsyncMock,
            return_value=mock_root_cause,
        ),
        patch.object(
            orchestrator._remediation,
            "run",
            new_callable=AsyncMock,
            return_value=mock_remediation,
        ),
    ):
        events: list[StreamEvent] = []
        async for event in orchestrator.run_with_stream(
            "Checkout service is slow", "test-session"
        ):
            events.append(event)

    event_types = [e.event for e in events]
    assert "step" in event_types
    assert "result" in event_types

    result_event = next(e for e in events if e.event == "result")
    assert result_event.data is not None
    assert "session_id" in result_event.data
    assert "root_cause" in result_event.data
    assert "remediation_steps" in result_event.data


@pytest.mark.asyncio
async def test_orchestrator_handles_agent_errors(mock_classification):
    orchestrator = IncidentOrchestrator()

    with (
        patch.object(
            orchestrator._classifier,
            "run",
            new_callable=AsyncMock,
            return_value=mock_classification,
        ),
        patch.object(
            orchestrator._searcher,
            "run",
            new_callable=AsyncMock,
            side_effect=Exception("Searcher crashed"),
        ),
        patch.object(
            orchestrator._graph_agent,
            "run",
            new_callable=AsyncMock,
            side_effect=Exception("Graph unreachable"),
        ),
        patch.object(
            orchestrator._root_cause,
            "run",
            new_callable=AsyncMock,
            side_effect=Exception("RCA failed"),
        ),
        patch.object(
            orchestrator._remediation,
            "run",
            new_callable=AsyncMock,
            side_effect=Exception("Remediation failed"),
        ),
    ):
        events: list[StreamEvent] = []
        async for event in orchestrator.run_with_stream(
            "Test incident", "test-session"
        ):
            events.append(event)

    result_events = [e for e in events if e.event == "result"]
    assert len(result_events) == 1

    error_events = [e for e in events if e.status == "error"]
    assert len(error_events) > 0
