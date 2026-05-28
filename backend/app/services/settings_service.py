from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets import decrypt_secret, encrypt_secret
from app.db.models import User, UserSettings
from app.schemas.settings import (
    GitHubConfigPayload,
    LLMConfigPayload,
    SettingsResponse,
    TerraformConfigPayload,
    UserPreferencesPayload,
    UserPreferencesResponse,
)
from logger import logger
from settings import settings


class SettingsService:
    def __init__(self, db: AsyncSession | None = None) -> None:
        self._db = db

    def apply_llm(self, payload: LLMConfigPayload) -> None:
        if payload.provider:
            settings.LLM_PROVIDER = payload.provider

        if payload.api_key:
            settings.OPENAI_API_KEY = payload.api_key
            settings.ANTHROPIC_API_KEY = payload.api_key
            settings.GOOGLE_API_KEY = payload.api_key

            provider_env = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "google": "GOOGLE_API_KEY",
            }.get(payload.provider, "OPENAI_API_KEY")

            os.environ[provider_env] = payload.api_key

        settings.OPENAI_BASE_URL = payload.base_url

        if payload.base_url:
            os.environ["OPENAI_BASE_URL"] = payload.base_url
            os.environ["OPENAI_API_BASE"] = payload.base_url
        else:
            os.environ.pop("OPENAI_BASE_URL", None)
            os.environ.pop("OPENAI_API_BASE", None)

        if payload.model_name:
            settings.LLM_MODEL = payload.model_name

        settings.LLM_TEMPERATURE = payload.temperature
        settings.LLM_MAX_RETRIES = payload.max_retries

    def apply_github(self, payload: GitHubConfigPayload, oauth_token: str = "") -> None:
        token = oauth_token if payload.github_use_oauth and oauth_token else payload.github_token

        if token:
            settings.GITHUB_TOKEN = token
            os.environ["GITHUB_TOKEN"] = token
            os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = token

        if payload.github_repo:
            os.environ["GITHUB_REPO"] = payload.github_repo

    def apply_terraform(self, payload: TerraformConfigPayload) -> None:
        if payload.terraform_token:
            os.environ["TERRAFORM_CLOUD_TOKEN"] = payload.terraform_token
            os.environ["TF_TOKEN_app_terraform_io"] = payload.terraform_token

        if payload.terraform_workspace:
            os.environ["TERRAFORM_WORKSPACE"] = payload.terraform_workspace

    async def get_or_create_user_settings(self, user: User) -> UserSettings:
        if self._db is None:
            raise RuntimeError("Database session is required for persisted preferences.")

        result = await self._db.execute(select(UserSettings).where(UserSettings.user_id == user.id))
        row = result.scalar_one_or_none()

        if row:
            return row

        row = UserSettings(user_id=user.id)
        self._db.add(row)
        await self._db.commit()
        await self._db.refresh(row)
        return row

    async def get_preferences(self, user: User) -> UserPreferencesResponse:
        row = await self.get_or_create_user_settings(user)

        oauth_token = decrypt_secret(user.oauth_access_token_encrypted)
        github_oauth_connected = user.oauth_provider == "github" and bool(oauth_token)

        return UserPreferencesResponse(
            user_id=str(user.id),
            llm=LLMConfigPayload(
                provider=row.llm_provider,
                api_key=decrypt_secret(row.llm_api_key_encrypted),
                base_url=row.llm_base_url,
                model_name=row.llm_model_name,
                temperature=row.llm_temperature,
                max_retries=row.llm_max_retries,
            ),
            github=GitHubConfigPayload(
                github_token=decrypt_secret(row.github_token_encrypted),
                github_repo=row.github_repo,
                github_use_oauth=row.github_use_oauth and github_oauth_connected,
                github_oauth_connected=github_oauth_connected,
            ),
            terraform=TerraformConfigPayload(
                terraform_token=decrypt_secret(row.terraform_token_encrypted),
                terraform_workspace=row.terraform_workspace,
            ),
        )

    async def save_preferences(
        self,
        user: User,
        payload: UserPreferencesPayload,
    ) -> UserPreferencesResponse:
        if self._db is None:
            raise RuntimeError("Database session is required for persisted preferences.")

        row = await self.get_or_create_user_settings(user)

        row.llm_provider = payload.llm.provider
        row.llm_api_key_encrypted = (
            encrypt_secret(payload.llm.api_key) if payload.llm.api_key else ""
        )
        row.llm_base_url = payload.llm.base_url
        row.llm_model_name = payload.llm.model_name
        row.llm_temperature = payload.llm.temperature
        row.llm_max_retries = payload.llm.max_retries

        row.github_token_encrypted = (
            encrypt_secret(payload.github.github_token) if payload.github.github_token else ""
        )
        row.github_repo = payload.github.github_repo
        row.github_use_oauth = payload.github.github_use_oauth

        row.terraform_token_encrypted = (
            encrypt_secret(payload.terraform.terraform_token)
            if payload.terraform.terraform_token
            else ""
        )
        row.terraform_workspace = payload.terraform.terraform_workspace

        await self._db.commit()
        await self._db.refresh(row)

        oauth_token = decrypt_secret(user.oauth_access_token_encrypted)
        self.apply_llm(payload.llm)
        self.apply_github(payload.github, oauth_token=oauth_token)
        self.apply_terraform(payload.terraform)

        return await self.get_preferences(user)

    def update_runtime_llm(self, payload: LLMConfigPayload) -> SettingsResponse:
        self.apply_llm(payload)
        logger.info(
            f"[Settings] Runtime LLM config updated provider={payload.provider} model={payload.model_name}"
        )
        return SettingsResponse(
            status="ok", message="LLM configuration applied to running process."
        )

    def update_runtime_github(self, payload: GitHubConfigPayload) -> SettingsResponse:
        self.apply_github(payload)
        logger.info("[Settings] Runtime GitHub configuration updated.")
        return SettingsResponse(status="ok", message="GitHub configuration applied.")

    def update_runtime_terraform(self, payload: TerraformConfigPayload) -> SettingsResponse:
        self.apply_terraform(payload)
        logger.info("[Settings] Runtime Terraform configuration updated.")
        return SettingsResponse(status="ok", message="Terraform configuration applied.")
