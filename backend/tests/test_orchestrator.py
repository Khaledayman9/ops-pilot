from unittest.mock import AsyncMock, patch

import pytest

from app.agents.orchestrator.graph import IncidentOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_streams_all_steps(
    mock_classification,
    mock_search_output,
    mock_graph_output,
    mock_root_cause,
    mock_remediation,
):
    o = IncidentOrchestrator()
    with (
        patch.object(
            o._classifier, "run", new_callable=AsyncMock, return_value=mock_classification
        ),
        patch.object(o._extractor, "run", new_callable=AsyncMock, return_value=mock_search_output),
        patch.object(o._graph, "run", new_callable=AsyncMock, return_value=mock_graph_output),
        patch.object(
            o._web_searcher,
            "run",
            new_callable=AsyncMock,
            return_value=type("WO", (), {"combined_context": "ctx", "results": []})(),
        ),
        patch.object(o._crew, "run", new_callable=AsyncMock, return_value="crew report"),
        patch.object(o._root_cause, "run", new_callable=AsyncMock, return_value=mock_root_cause),
        patch.object(o._remediator, "run", new_callable=AsyncMock, return_value=mock_remediation),
    ):
        events = [e async for e in o.run_with_stream("Checkout slow", "test-session")]

    assert any(e.event == "result" for e in events)
    result = next(e for e in events if e.event == "result")
    assert "root_cause" in result.data
    assert "remediation_steps" in result.data
    assert "graph_context" in result.data


@pytest.mark.asyncio
async def test_orchestrator_handles_agent_errors(mock_classification):
    o = IncidentOrchestrator()
    with (
        patch.object(
            o._classifier, "run", new_callable=AsyncMock, return_value=mock_classification
        ),
        patch.object(o._extractor, "run", new_callable=AsyncMock, side_effect=Exception("boom")),
        patch.object(o._graph, "run", new_callable=AsyncMock, side_effect=Exception("boom")),
        patch.object(o._web_searcher, "run", new_callable=AsyncMock, side_effect=Exception("boom")),
        patch.object(o._crew, "run", new_callable=AsyncMock, side_effect=Exception("boom")),
        patch.object(o._root_cause, "run", new_callable=AsyncMock, side_effect=Exception("boom")),
        patch.object(o._remediator, "run", new_callable=AsyncMock, side_effect=Exception("boom")),
    ):
        events = [e async for e in o.run_with_stream("Test", "test-session")]

    assert sum(1 for e in events if e.event == "result") == 1
    assert any(e.status == "error" for e in events)
