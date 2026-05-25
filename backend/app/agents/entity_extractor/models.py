from pydantic import BaseModel, Field


class EntityExtractorInput(BaseModel):
    query: str
    service: str
    incident_type: str


class EntityExtraction(BaseModel):
    services: list[str] = Field(default_factory=list)
    deployments: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    time_range: str | None = None
    error_codes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class EntityExtractorOutput(BaseModel):
    entities: EntityExtraction
    search_queries: list[str] = Field(default_factory=list)
    context_summary: str
