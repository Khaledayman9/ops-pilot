from pydantic import BaseModel, Field


class IncidentRequest(BaseModel):
    query: str = Field(..., description="Incident description from the user")
    session_id: str | None = Field(None)


class IncidentResponse(BaseModel):
    session_id: str
    classification: dict
    graph_context: dict
    root_cause: str
    blast_radius: dict
    remediation_steps: list[str]
    timeline: list[str]