"""
Runtime settings endpoint.
Allows the frontend to push LLM and GitHub config into the running process
without a restart. Values are applied to `settings` in-process only —
they do not persist to disk (use .env for permanent changes).
"""

from __future__ import annotations

import os

from fastapi import APIRouter


from logger import logger
from settings import settings
from app.schemas.settings import SettingsResponse, GitHubConfigPayload, LLMConfigPayload

router = APIRouter()


@router.post("/llm", response_model=SettingsResponse)
async def update_llm_config(payload: LLMConfigPayload) -> SettingsResponse:
    """
    Apply LLM provider settings to the running process.
    Only non-empty values overwrite the current settings.
    """
    if payload.provider:
        settings.LLM_PROVIDER = payload.provider
    if payload.api_key:
        settings.OPENAI_API_KEY = payload.api_key
        settings.ANTHROPIC_API_KEY = payload.api_key
        settings.GOOGLE_API_KEY = payload.api_key
        # Set the correct key env var for the provider
        provider_env = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }.get(payload.provider, "OPENAI_API_KEY")
        os.environ[provider_env] = payload.api_key
    if payload.base_url:
        settings.OPENAI_BASE_URL = payload.base_url
        os.environ["OPENAI_BASE_URL"] = payload.base_url
    if payload.model_name:
        settings.LLM_MODEL = payload.model_name
    settings.LLM_TEMPERATURE = payload.temperature
    settings.LLM_MAX_RETRIES = payload.max_retries

    logger.info(
        f"[Settings] LLM config updated: provider={payload.provider} "
        f"model={payload.model_name} temperature={payload.temperature}"
    )
    return SettingsResponse(status="ok", message="LLM configuration applied to running process.")


@router.post("/github", response_model=SettingsResponse)
async def update_github_config(payload: GitHubConfigPayload) -> SettingsResponse:
    """
    Apply GitHub token to the running process.
    This is picked up by the MCP client manager when it next spawns the
    mcp-server-github process (${GITHUB_TOKEN} interpolation in servers.json).
    """
    if payload.github_token:
        settings.GITHUB_TOKEN = payload.github_token
        os.environ["GITHUB_TOKEN"] = payload.github_token
        logger.info("[Settings] GitHub token updated.")
    if payload.github_repo:
        os.environ["GITHUB_REPO"] = payload.github_repo
        logger.info(f"[Settings] GitHub default repo set to: {payload.github_repo}")
    return SettingsResponse(status="ok", message="GitHub configuration applied.")


@router.get("/", response_model=dict)
async def get_current_settings() -> dict:
    """Return non-sensitive current settings for the frontend to display."""
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "llm_temperature": settings.LLM_TEMPERATURE,
        "llm_max_retries": settings.LLM_MAX_RETRIES,
        "openai_base_url": settings.OPENAI_BASE_URL,
        "github_token_set": bool(settings.GITHUB_TOKEN),
        "pii_scrubbing": settings.ENABLE_PII_SCRUBBING,
        "injection_protection": settings.ENABLE_PROMPT_INJECTION_PROTECTION,
    }
