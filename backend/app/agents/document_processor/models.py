from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentProcessorInput(BaseModel):
    file_path: str = Field(..., description="Local path or URL to the uploaded document. Pass '__inline__' when inline_content is provided.")
    filename: str = Field(..., description="Original filename")
    mime_type: str | None = Field(default=None, description="Uploaded file MIME type")
    inline_content: str | None = Field(
        default=None,
        description="Pre-converted markdown content. When set, file_path is ignored and this content is used directly, allowing the agent to be called on already-processed markdown for metadata recording and normalisation.",
    )


class DocumentProcessorOutput(BaseModel):
    filename: str
    markdown: str
    chunks: int = 0
    characters: int = 0
    mime_type: str | None = None
