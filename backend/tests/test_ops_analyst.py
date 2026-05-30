"""Tests for OpsAnalystAgent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.ops_analyst import OpsAnalystAgent
from app.agents.ops_analyst.models import AnalysisTask, OpsAnalystInput, OpsAnalystOutput


@pytest.fixture
def base_input_general():
    return OpsAnalystInput(
        task=AnalysisTask.GENERAL,
        payload="Checkout service p99 latency is 3.2s. Error rate is 12%. Memory at 92%.",
        service_name="checkout-service",
    )


@pytest.fixture
def base_input_error_rate():
    return OpsAnalystInput(
        task=AnalysisTask.CALCULATE_ERROR_RATE,
        payload="total_requests=10000, error_count=1200, window_minutes=5",
        service_name="checkout-service",
    )


@pytest.fixture
def base_input_stack_trace():
    return OpsAnalystInput(
        task=AnalysisTask.PARSE_STACK_TRACE,
        payload=(
            "java.lang.OutOfMemoryError: GC overhead limit exceeded\n"
            "  at com.example.checkout.db.PoolManager.acquire(PoolManager.java:142)\n"
            "  at com.example.checkout.service.OrderService.create(OrderService.java:88)"
        ),
        service_name="checkout-service",
    )


@pytest.fixture
def mock_ops_output():
    return OpsAnalystOutput(
        task="general",
        service_name="checkout-service",
        result=(
            "Telemetry Analysis — checkout-service\n\n"
            "ERROR RATE: 12.0% (critical threshold: 5%)\n"
            "P99 LATENCY: 3200ms (SLO: 500ms) — BREACHED\n"
            "MEMORY: 92% utilisation — approaching OOM\n\n"
            "Diagnosis: High memory pressure is causing GC pauses which directly "
            "inflate p99 latency. Error rate rise is consistent with DB connection "
            "timeouts caused by pool exhaustion under GC pauses.\n\n"
            "Recommended: Immediate pod scale-up and memory profiling."
        ),
        tools_used=["calculate_error_rate", "check_service_health", "format_incident_brief"],
    )


@pytest.mark.asyncio
async def test_ops_analyst_returns_output(base_input_general, mock_ops_output):
    agent = OpsAnalystAgent()
    agent._initialized = True
    agent._tool_names = mock_ops_output.tools_used

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(
                return_value={"messages": [MagicMock(content=mock_ops_output.result)]}
            )
            result = await agent.run(base_input_general)

    assert isinstance(result, OpsAnalystOutput)
    assert result.result != ""
    assert result.service_name == "checkout-service"


@pytest.mark.asyncio
async def test_ops_analyst_task_enum_values():
    """All AnalysisTask enum values should be valid strings."""
    assert AnalysisTask.GENERAL == "general"
    assert AnalysisTask.PARSE_STACK_TRACE == "parse_stack_trace"
    assert AnalysisTask.CALCULATE_ERROR_RATE == "calculate_error_rate"
    assert AnalysisTask.FORMAT_INCIDENT_BRIEF == "format_incident_brief"
    assert AnalysisTask.CHECK_SERVICE_HEALTH == "check_service_health"


@pytest.mark.asyncio
async def test_ops_analyst_error_rate_task(base_input_error_rate, mock_ops_output):
    agent = OpsAnalystAgent()
    agent._initialized = True
    agent._tool_names = ["calculate_error_rate"]

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(
                return_value={"messages": [MagicMock(content="Error rate: 12.0% (CRITICAL)")]}
            )
            result = await agent.run(base_input_error_rate)

    assert isinstance(result, OpsAnalystOutput)
    assert result.task == AnalysisTask.CALCULATE_ERROR_RATE.value


@pytest.mark.asyncio
async def test_ops_analyst_stack_trace_task(base_input_stack_trace, mock_ops_output):
    agent = OpsAnalystAgent()
    agent._initialized = True
    agent._tool_names = ["parse_stack_trace"]

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(
                return_value={
                    "messages": [
                        MagicMock(
                            content="Stack trace points to PoolManager.acquire at line 142. OOM under GC pressure."
                        )
                    ]
                }
            )
            result = await agent.run(base_input_stack_trace)

    assert isinstance(result, OpsAnalystOutput)
    assert result.task == AnalysisTask.PARSE_STACK_TRACE.value


@pytest.mark.asyncio
async def test_ops_analyst_timeout_graceful(base_input_general):
    """asyncio.TimeoutError should return a graceful non-raising OpsAnalystOutput."""
    import asyncio

    agent = OpsAnalystAgent()
    agent._initialized = True
    agent._tool_names = []

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(side_effect=asyncio.TimeoutError)
            result = await agent.run(base_input_general)

    assert isinstance(result, OpsAnalystOutput)
    assert "timed out" in result.result.lower() or result.result != ""


@pytest.mark.asyncio
async def test_ops_analyst_mcp_init_failure_raises():
    """If ops-inspector MCP is not configured, initialization should raise."""
    agent = OpsAnalystAgent()
    with patch("json.load", return_value={}):
        with patch("builtins.open", MagicMock()):
            with pytest.raises((ValueError, FileNotFoundError, RuntimeError)):
                await agent._load_ops_tools()


@pytest.mark.asyncio
async def test_ops_analyst_tools_used_in_output(base_input_general, mock_ops_output):
    agent = OpsAnalystAgent()
    agent._initialized = True
    agent._tool_names = mock_ops_output.tools_used

    with patch.object(agent, "_initialize", new_callable=AsyncMock):
        with patch.object(agent, "_agent") as mock_agent_obj:
            mock_agent_obj.ainvoke = AsyncMock(
                return_value={"messages": [MagicMock(content=mock_ops_output.result)]}
            )
            result = await agent.run(base_input_general)

    assert isinstance(result.tools_used, list)


@pytest.mark.asyncio
async def test_ops_analyst_inherits_base_agent():
    from app.core.base_agent import BaseAgent

    agent = OpsAnalystAgent()
    assert isinstance(agent, BaseAgent)
    assert agent.agent_name == "ops_analyst"


@pytest.mark.asyncio
async def test_ops_analyst_loads_prompts():
    agent = OpsAnalystAgent()
    assert "system" in agent._prompts
    assert "user_template" in agent._prompts


def test_ops_analyst_input_schema():
    inp = OpsAnalystInput(
        task=AnalysisTask.CHECK_SERVICE_HEALTH,
        payload="service=payment-service",
        service_name="payment-service",
    )
    assert inp.task == AnalysisTask.CHECK_SERVICE_HEALTH
    assert inp.service_name == "payment-service"


def test_ops_analyst_output_schema():
    out = OpsAnalystOutput(
        task="general",
        service_name="redis",
        result="CPU at 95%. Memory at 88%. No recent deployments.",
        tools_used=["check_service_health"],
    )
    assert out.task == "general"
    assert len(out.tools_used) == 1
