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
    affected_services: list[ServiceNode]
    dependency_edges: list[DependencyEdge]
    upstream_services: list[str]
    downstream_services: list[str]
    blast_radius_count: int
    recent_deployments: list[dict]
    related_incidents: list[dict]
    graph_summary: str
