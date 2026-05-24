"""
Authentication endpoints.

POST /api/v1/auth/register   — create account
POST /api/v1/auth/login      — get tokens
POST /api/v1/auth/refresh    — rotate access token using refresh token
GET  /api/v1/auth/me         — return current user (requires Bearer)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.postgres import get_db
from app.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPublic,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=201,
    summary="Register a new user account",
)
async def register(
    payload: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserPublic:
    return await AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse, summary="Obtain JWT tokens")
async def login(
    payload: UserLogin, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    return await AuthService(db).login(payload)


@router.post("/refresh", response_model=TokenResponse, summary="Rotate access token")
async def refresh(
    payload: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    return await AuthService(db).refresh(payload.refresh_token)


@router.get("/me", response_model=UserPublic, summary="Return authenticated user")
async def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current_user)
