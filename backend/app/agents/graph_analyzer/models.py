from pydantic import BaseModel, Field


class ServiceNode(BaseModel):
    name: str
    type: str
    status: str
    team: str | None = None


class DependencyEdge(BaseModel):
    source: str
    target: str
    relation: str


class GraphAnalyzerQueryInput(BaseModel):
    service: str
    entities: list[str] = Field(default_factory=list)
    incident_type: str


class GraphAnalyzerQueryOutput(BaseModel):
    affected_services: list[ServiceNode] = Field(default_factory=list)
    dependency_edges: list[DependencyEdge] = Field(default_factory=list)
    upstream_services: list[str] = Field(default_factory=list)
    downstream_services: list[str] = Field(default_factory=list)
    blast_radius_count: int = 0
    recent_deployments: list[dict] = Field(default_factory=list)
    related_incidents: list[dict] = Field(default_factory=list)
    graph_summary: str = ""
