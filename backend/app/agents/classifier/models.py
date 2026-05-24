from pydantic import BaseModel, Field


class ClassificationInput(BaseModel):
    query: str = Field(..., description="Raw incident query from user")


class ClassificationOutput(BaseModel):
    service: str = Field(..., description="Primary affected service name")
    severity: str = Field(..., description="Severity level: P0 | P1 | P2 | P3")
    incident_type: str = Field(
        ...,
        description="Type: latency | error_rate | outage | degradation | deployment",
    )
    affected_components: list[str] = Field(default_factory=list)
    trigger_event: str | None = Field(
        None, description="e.g. deployment, config change"
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
