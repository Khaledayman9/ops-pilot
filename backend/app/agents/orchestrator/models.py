from pydantic import BaseModel, Field


class IncidentState(BaseModel):
    query: str
    session_id: str

    service: str | None = None
    severity: str | None = None
    incident_type: str | None = None
    affected_components: list[str] = Field(default_factory=list)
    trigger_event: str | None = None
    classification: dict = Field(default_factory=dict)

    entities: dict = Field(default_factory=dict)
    graph_context: dict = Field(default_factory=dict)

    root_cause: str | None = None
    causal_chain: list[dict] = Field(default_factory=list)
    deployment_correlation: bool = False
    deployment_version: str | None = None
    timeline: list[str] = Field(default_factory=list)

    remediation_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    escalation_paths: list[dict] = Field(default_factory=list)
    runbook_references: list[str] = Field(default_factory=list)

    current_step: str = "start"
    errors: list[str] = Field(default_factory=list)
    completed_steps: list[str] = Field(default_factory=list)
