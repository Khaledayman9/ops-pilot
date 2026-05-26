"""
Auth service — registration, login, token refresh.
Follows the principle: thin routes, fat services.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserPublic
from logger import logger

__all__ = ["AuthService"]


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def register(self, payload: UserCreate) -> UserPublic:
        # Uniqueness check
        existing = await self._db.execute(
            select(User).where((User.email == payload.email) | (User.username == payload.username))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or username already registered.",
            )

        user = User(
            email=payload.email,
            username=payload.username,
            hashed_password=hash_password(payload.password),
        )
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        logger.info(f"[AuthService] Registered user {user.email}")
        return UserPublic.model_validate(user)

    async def login(self, payload: UserLogin) -> TokenResponse:
        result = await self._db.execute(select(User).where(User.email == payload.email))
        user: User | None = result.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated.",
            )

        subject = str(user.id)
        logger.info(f"[AuthService] Login for {user.email}")
        return TokenResponse(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            ) from exc

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token type mismatch.",
            )

        subject = payload["sub"]
        return TokenResponse(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        )

    async def get_current_user(self, token: str) -> User:
        try:
            payload = decode_token(token)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token type mismatch.",
            )

        user_id = uuid.UUID(payload["sub"])
        result = await self._db.execute(select(User).where(User.id == user_id))
        user: User | None = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive.",
            )
        return user
