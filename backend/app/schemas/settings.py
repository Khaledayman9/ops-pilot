from pydantic import BaseModel


class LLMConfigPayload(BaseModel):
    provider: str = "openai"
    api_key: str = ""
    base_url: str = ""
    model_name: str = "gpt-4o"
    temperature: float = 0.0
    max_retries: int = 3


class GitHubConfigPayload(BaseModel):
    github_token: str = ""
    github_repo: str = ""


class UserPreferencesPayload(BaseModel):
    llm: LLMConfigPayload = LLMConfigPayload()
    github: GitHubConfigPayload = GitHubConfigPayload()


class UserPreferencesResponse(UserPreferencesPayload):
    user_id: str | None = None


class SettingsResponse(BaseModel):
    status: str
    message: str
