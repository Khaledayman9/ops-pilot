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
    github_use_oauth: bool = False
    github_oauth_connected: bool = False


class TerraformConfigPayload(BaseModel):
    terraform_token: str = ""
    terraform_workspace: str = ""


class UserPreferencesPayload(BaseModel):
    llm: LLMConfigPayload = LLMConfigPayload()
    github: GitHubConfigPayload = GitHubConfigPayload()
    terraform: TerraformConfigPayload = TerraformConfigPayload()


class UserPreferencesResponse(UserPreferencesPayload):
    user_id: str | None = None


class SettingsResponse(BaseModel):
    status: str
    message: str
