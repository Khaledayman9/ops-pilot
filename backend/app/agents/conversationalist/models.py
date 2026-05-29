from __future__ import annotations

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ConversationalistInput(BaseModel):
    query: str = Field(..., description="Current user message")
    history: list[ChatTurn] = Field(
        default_factory=list,
        description="Compacted conversation history turns",
    )
    incident_structured: dict | None = Field(
        None,
        description="Full structured result data from the orchestrator (None for irrelevant queries)",
    )
    web_citations: list[dict] = Field(
        default_factory=list,
        description="List of web search citations with title and url",
    )
    is_incident_query: bool = Field(
        True,
        description="Whether the query is relevant to incident analysis",
    )
    analysis_context: str = Field(
        "",
        description="Summarised textual context from the pipeline (root cause, remediation, etc.)",
    )


class ConversationalistOutput(BaseModel):
    natural_response: str = Field(
        ...,
        description="Human-readable conversational explanation of the analysis or general response",
    )
    is_incident_relevant: bool = Field(
        ...,
        description="True if the query was incident-relevant and structured analysis was performed",
    )
    summary_for_history: str = Field(
        ...,
        description="A concise ≤120-word summary of this turn for chat-history compaction",
    )
