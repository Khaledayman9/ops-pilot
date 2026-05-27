from __future__ import annotations

import os
import uuid

import httpx
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


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def register(self, payload: UserCreate) -> UserPublic:
        existing = await self._db.execute(
            select(User).where((User.email == payload.email) | (User.username == payload.username))
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email or username already registered."
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

        if (
            not user
            or not user.hashed_password
            or not verify_password(payload.password, user.hashed_password)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated."
            )

        return self._tokens_for_user(user)

    async def oauth_login(self, provider: str, code: str, redirect_uri: str) -> TokenResponse:
        if provider == "google":
            profile = await self._google_profile(code, redirect_uri)
        elif provider == "github":
            profile = await self._github_profile(code, redirect_uri)
        else:
            raise HTTPException(status_code=400, detail="Unsupported OAuth provider.")

        email = profile["email"]
        subject = profile["sub"]
        username = profile.get("username") or email.split("@")[0]

        result = await self._db.execute(
            select(User).where((User.oauth_provider == provider) & (User.oauth_subject == subject))
        )
        user = result.scalar_one_or_none()

        if not user:
            result = await self._db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

        if not user:
            base_username = username.replace(" ", "_").replace("-", "_")[:48]
            candidate = base_username
            suffix = 1
            while True:
                existing = await self._db.execute(select(User).where(User.username == candidate))
                if not existing.scalar_one_or_none():
                    break
                suffix += 1
                candidate = f"{base_username}_{suffix}"

            user = User(
                email=email,
                username=candidate,
                hashed_password=None,
                oauth_provider=provider,
                oauth_subject=subject,
                is_verified=True,
            )
            self._db.add(user)
        else:
            user.oauth_provider = user.oauth_provider or provider
            user.oauth_subject = user.oauth_subject or subject
            user.is_verified = True

        await self._db.commit()
        await self._db.refresh(user)
        return self._tokens_for_user(user)

    async def _google_profile(self, code: str, redirect_uri: str) -> dict[str, str]:
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Google OAuth is not configured.")

        async with httpx.AsyncClient(timeout=20) as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            token_res.raise_for_status()
            access_token = token_res.json()["access_token"]

            profile_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_res.raise_for_status()
            profile = profile_res.json()

        return {
            "sub": profile["sub"],
            "email": profile["email"],
            "username": profile.get("name") or profile["email"].split("@")[0],
        }

    async def _github_profile(self, code: str, redirect_uri: str) -> dict[str, str]:
        client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID", "")
        client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="GitHub OAuth is not configured.")

        async with httpx.AsyncClient(timeout=20) as client:
            token_res = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
            token_res.raise_for_status()
            access_token = token_res.json()["access_token"]

            user_res = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            user_res.raise_for_status()
            gh_user = user_res.json()

            email = gh_user.get("email")
            if not email:
                email_res = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )
                email_res.raise_for_status()
                emails = email_res.json()
                primary = next((item for item in emails if item.get("primary")), emails[0])
                email = primary["email"]

        return {
            "sub": str(gh_user["id"]),
            "email": email,
            "username": gh_user.get("login") or email.split("@")[0],
        }

    def _tokens_for_user(self, user: User) -> TokenResponse:
        subject = str(user.id)
        return TokenResponse(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token."
            ) from exc

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token type mismatch."
            )

        return TokenResponse(
            access_token=create_access_token(payload["sub"]),
            refresh_token=create_refresh_token(payload["sub"]),
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
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token type mismatch."
            )

        result = await self._db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
        user: User | None = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive."
            )
        return user
