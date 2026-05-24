from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str

    def to_text(self) -> str:
        return f"{self.title}. {self.snippet}"


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query derived from the incident")
    max_results: int = Field(default=5, ge=1, le=10)


class WebSearchOutput(BaseModel):
    results: list[SearchResult]
    combined_context: str = Field(
        description="Flattened text of all results for LLM ingestion"
    )
    queries_used: list[str]
