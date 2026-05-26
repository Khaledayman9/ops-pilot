from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AnalysisTask(str, Enum):
    PARSE_STACK_TRACE = "parse_stack_trace"
    CALCULATE_ERROR_RATE = "calculate_error_rate"
    FORMAT_INCIDENT_BRIEF = "format_incident_brief"
    CHECK_SERVICE_HEALTH = "check_service_health"
    GENERAL = "general"


class OpsAnalystInput(BaseModel):
    task: AnalysisTask = Field(
        default=AnalysisTask.GENERAL,
        description="Which ops tool to invoke, or 'general' for free-form analysis.",
    )
    payload: str = Field(
        ...,
        description=(
            "Natural language request or raw data for the agent to process "
            "(e.g. a stack trace, error counts, service name)."
        ),
    )
    service_name: str = Field(default="unknown", description="Affected service name")


class OpsAnalystOutput(BaseModel):
    task: str
    service_name: str
    result: str = Field(description="Final structured answer from the agent")
    tools_used: list[str] = Field(default_factory=list)
