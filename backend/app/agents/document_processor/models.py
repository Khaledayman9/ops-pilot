from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentProcessorInput(BaseModel):
    file_path: str = Field(..., description="Local path or URL to the uploaded document")
    filename: str = Field(..., description="Original filename")
    mime_type: str | None = Field(default=None, description="Uploaded file MIME type")


class DocumentProcessorOutput(BaseModel):
    filename: str
    markdown: str
    chunks: int = 0
    characters: int = 0
    mime_type: str | None = None
