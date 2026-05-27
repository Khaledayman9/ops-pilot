from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.postgres import get_db
from app.schemas.settings import (
    GitHubConfigPayload,
    LLMConfigPayload,
    SettingsResponse,
    UserPreferencesPayload,
    UserPreferencesResponse,
)
from app.services.settings_service import SettingsService
from settings import settings

router = APIRouter()


@router.post("/llm", response_model=SettingsResponse)
async def update_llm_config(payload: LLMConfigPayload) -> SettingsResponse:
    return SettingsService().update_runtime_llm(payload)


@router.post("/github", response_model=SettingsResponse)
async def update_github_config(payload: GitHubConfigPayload) -> SettingsResponse:
    return SettingsService().update_runtime_github(payload)


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserPreferencesResponse:
    return await SettingsService(db).get_preferences(current_user)


@router.put("/preferences", response_model=UserPreferencesResponse)
async def save_user_preferences(
    payload: UserPreferencesPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserPreferencesResponse:
    return await SettingsService(db).save_preferences(current_user, payload)


@router.get("/", response_model=dict)
async def get_current_settings() -> dict:
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
