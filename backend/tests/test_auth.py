"""Auth endpoint tests."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.schemas.auth import UserPublic, TokenResponse
import uuid


@pytest.mark.asyncio
async def test_register_endpoint():
    mock_user = UserPublic(
        id=str(uuid.uuid4()),
        email="test@example.com",
        username="testuser",
        is_active=True,
        is_verified=False,
    )
    with patch("app.api.routes.auth.AuthService") as MockSvc:
        instance = MockSvc.return_value
        instance.register = AsyncMock(return_value=mock_user)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            r = await c.post(
                "/api/v1/auth/register",
                json={
                    "email": "test@example.com",
                    "username": "testuser",
                    "password": "secret123",
                },
            )
    assert r.status_code == 201
    assert r.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_endpoint():
    mock_tokens = TokenResponse(
        access_token="access.token.here",
        refresh_token="refresh.token.here",
    )
    with patch("app.api.routes.auth.AuthService") as MockSvc:
        instance = MockSvc.return_value
        instance.login = AsyncMock(return_value=mock_tokens)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            r = await c.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "secret123"},
            )
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
