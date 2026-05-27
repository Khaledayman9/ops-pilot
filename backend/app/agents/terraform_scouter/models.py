from __future__ import annotations

from pydantic import BaseModel, Field


class TerraformScoutInput(BaseModel):
    task: str = Field(default="summarize", description="Terraform/IaC task to run")
    workspace: str = Field(default="", description="Terraform workspace or stack")
    extra_context: str = Field(default="", description="Incident context")


class TerraformScoutOutput(BaseModel):
    task: str
    workspace: str = ""
    summary: str
    tools_used: list[str] = Field(default_factory=list)
