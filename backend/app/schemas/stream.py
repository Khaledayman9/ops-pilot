from pydantic import BaseModel, Field


class StreamEvent(BaseModel):
    event: str = Field(..., description="step | graph | reasoning | result | error")
    agent: str | None = None
    step: str | None = None
    data: dict | str | None = None
    status: str | None = None