from __future__ import annotations

from pydantic import BaseModel, Field


class RepoSummary(BaseModel):
    full_name: str = ""
    default_branch: str = ""
    open_issues: int = 0
    stars: int = 0
    language: str | None = None


class RepoScoutInput(BaseModel):
    owner: str = Field(..., description="GitHub organisation or username")
    repo: str = Field(..., description="Repository name")
    task: str = Field(
        default="summarize",
        description=(
            "What to fetch. Examples: 'summarize', 'list_branches', "
            "'recent_issues', 'open_prs', 'latest_commit'"
        ),
    )
    extra_context: str = Field(default="", description="Optional extra filters or instructions")


class RepoScoutOutput(BaseModel):
    owner: str
    repo: str
    task: str
    summary: str = Field(description="Human-readable LLM-produced summary")
    repo_info: RepoSummary = Field(default_factory=RepoSummary)
    tools_used: list[str] = Field(default_factory=list)
