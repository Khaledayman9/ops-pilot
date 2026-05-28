from __future__ import annotations

from urllib.parse import urlencode
from settings import settings

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.dtos import RefreshRequest, TokenResponse, UserCreate, UserLogin, UserPublic
from app.api.uris import AuthURIs
from app.db.models import User
from app.db.postgres import get_db
from app.schemas.auth import OAuthCallbackRequest, OAuthStartResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(AuthURIs.REGISTER, response_model=UserPublic, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserPublic:
    return await AuthService(db).register(payload)


@router.post(AuthURIs.LOGIN, response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await AuthService(db).login(payload)


@router.post(AuthURIs.REFRESH, response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await AuthService(db).refresh(payload.refresh_token)


@router.get(AuthURIs.ME, response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.get("/oauth/{provider}/start", response_model=OAuthStartResponse)
async def oauth_start(provider: str, redirect_uri: str) -> OAuthStartResponse:
    if provider == "google":
        query = urlencode(
            {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "access_type": "offline",
                "prompt": "select_account",
            }
        )
        return OAuthStartResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{query}")

    if provider == "github":
        query = urlencode(
            {
                "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "scope": "read:user user:email",
            }
        )
        return OAuthStartResponse(url=f"https://github.com/login/oauth/authorize?{query}")

    return OAuthStartResponse(url="")


@router.post("/oauth/{provider}/callback", response_model=TokenResponse)
async def oauth_callback(
    provider: str,
    payload: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await AuthService(db).oauth_login(provider, payload.code, payload.redirect_uri)
