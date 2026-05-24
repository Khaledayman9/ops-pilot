from pydantic import BaseModel, Field


class RemediationStep(BaseModel):
    order: int
    action: str
    command: str | None = None
    expected_outcome: str
    risk_level: str
    estimated_minutes: int


class EscalationPath(BaseModel):
    team: str
    contact: str
    condition: str


class RemediatorInput(BaseModel):
    service: str
    severity: str
    primary_cause: str
    causal_chain: list[dict]
    blast_radius: dict
    deployment_correlation: bool
    deployment_version: str | None


class RemediatorOutput(BaseModel):
    immediate_actions: list[RemediationStep]
    rollback_steps: list[RemediationStep]
    mitigation_steps: list[RemediationStep]
    escalation_paths: list[EscalationPath]
    runbook_references: list[str]
    estimated_resolution_minutes: int
    post_incident_actions: list[str]
    summary: str