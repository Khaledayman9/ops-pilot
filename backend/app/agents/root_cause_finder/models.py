from pydantic import BaseModel, Field


class CausalFactor(BaseModel):
    factor: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: str


class RootCauseFinderInput(BaseModel):
    query: str
    service: str
    incident_type: str
    severity: str
    graph_context: dict
    classification: dict


class RootCauseFinderOutput(BaseModel):
    primary_cause: str
    causal_chain: list[CausalFactor]
    contributing_factors: list[str]
    deployment_correlation: bool
    deployment_version: str | None = None
    timeline_reconstruction: list[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
