from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.dtos import RefreshRequest, TokenResponse, UserCreate, UserLogin, UserPublic
from app.api.uris import AuthURIs
from app.db.models import User
from app.db.postgres import get_db
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    AuthURIs.REGISTER,
    response_model=UserPublic,
    status_code=201,
    summary="Register a new user account",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    return await AuthService(db).register(payload)


@router.post(
    AuthURIs.LOGIN,
    response_model=TokenResponse,
    summary="Obtain JWT access + refresh tokens",
)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await AuthService(db).login(payload)


@router.post(
    AuthURIs.REFRESH,
    response_model=TokenResponse,
    summary="Rotate access token using a valid refresh token",
)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await AuthService(db).refresh(payload.refresh_token)


@router.get(
    AuthURIs.ME,
    response_model=UserPublic,
    summary="Return the currently authenticated user",
)
async def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)
