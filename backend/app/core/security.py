"""
JWT creation/verification and password hashing utilities.
All auth logic that is NOT HTTP-layer lives here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt

from settings import settings


import bcrypt


def hash_password(plain: str) -> str:
    truncated = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))


def _make_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str) -> str:
    """Create a short-lived JWT access token."""
    return _make_token(
        {"sub": subject, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: str) -> str:
    """Create a long-lived JWT refresh token."""
    return _make_token(
        {"sub": subject, "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT.

    Raises:
        JWTError: on invalid signature, expiry, or malformed token.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
