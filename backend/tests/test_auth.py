"""Tests for JWT cookie auth, refresh rotation, logout, and theft detection.

Covers Phase 2 tasks (2.1–2.5, 2.8):
- 2.1: Cookie-reading in auth middleware
- 2.2: Set-Cookie on login/register
- 2.3: Refresh token rotation with Redis blacklist
- 2.4: Logout endpoint
- 2.5: Theft detection
- 2.8: All auth tests
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from jose import jwt

from app.config import settings
from app.auth.utils import create_access_token, create_refresh_token


# ---------------------------------------------------------------------------
# Task 2.1: Cookie-reading in auth middleware
# ---------------------------------------------------------------------------


class TestGetTokenDependency:
    """The get_token() dependency must read cookies first, fall back to header."""

    async def test_cookie_takes_precedence_over_header(self, async_client: AsyncClient, test_user):
        """When both cookie and header are present, cookie value is used."""
        cookie_token = create_access_token(subject=test_user.id)
        header_token = create_access_token(subject="some-other-user-id")

        response = await async_client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {header_token}",
                "Cookie": f"access_token={cookie_token}",
            },
        )
        # Should return the user matching the cookie, not the header
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id

    async def test_header_fallback_when_no_cookie(self, async_client: AsyncClient, test_user):
        """When no cookie is present, the Authorization header is used."""
        token = create_access_token(subject=test_user.id)
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id

    async def test_unauthorized_when_no_auth(self, async_client: AsyncClient):
        """When neither cookie nor header is present, return 401."""
        response = await async_client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_unauthorized_with_invalid_cookie(self, async_client: AsyncClient):
        """When cookie is present but invalid, return 401."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Cookie": "access_token=invalid-token-value"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Task 2.2: Set-Cookie on login and register
# ---------------------------------------------------------------------------


class TestSetCookieOnAuth:
    """Login and register must set access_token as httpOnly cookie."""

    async def test_login_sets_cookie_and_returns_refresh_token(
        self, async_client: AsyncClient, test_user
    ):
        """Successful login sets Set-Cookie header and returns refresh_token in body."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "testpass123"},
        )
        assert response.status_code == 200
        body = response.json()
        # Must have refresh_token in body
        assert "refresh_token" in body
        assert "access_token" in body
        # Must have Set-Cookie header
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Path=/api" in set_cookie
        assert "Max-Age=900" in set_cookie

    async def test_register_sets_cookie_and_returns_refresh_token(
        self, async_client: AsyncClient, test_user, db_session
    ):
        """Successful registration sets Set-Cookie and returns refresh_token."""
        from app.models import User
        from sqlalchemy import select, text

        # Delete the pre-created test user so we can register with same email
        await db_session.execute(text("DELETE FROM \"user\" WHERE email = :e"), {"e": test_user.email})
        await db_session.commit()

        unique_email = f"new-{test_user.email}"
        response = await async_client.post(
            "/api/auth/register",
            json={"email": unique_email, "password": "TestPass123"},
        )
        assert response.status_code == 201
        body = response.json()
        assert "refresh_token" in body
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert "HttpOnly" in set_cookie

    async def test_login_with_wrong_password_does_not_set_cookie(
        self, async_client: AsyncClient, test_user
    ):
        """Failed login must NOT set a cookie."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "wrongpassword"},
        )
        assert response.status_code == 401
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" not in set_cookie


# ---------------------------------------------------------------------------
# Task 2.3: Refresh token rotation (Redis blacklist)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis():
    """Fixture that patches the Redis connection with an in-memory mock.

    We patch app.auth.redis_client.get_redis to return a mock Redis instance
    with async methods backed by a dict.
    """
    redis_data: dict[str, set[str]] = {}
    redis_hash: dict[str, str] = {}

    class MockRedisInstance:
        """In-memory mock of async Redis client methods used by auth."""

        async def sadd(self, key: str, value: str) -> None:
            if key not in redis_data:
                redis_data[key] = set()
            redis_data[key].add(value)

        async def sismember(self, key: str, value: str) -> bool:
            return value in redis_data.get(key, set())

        async def smembers(self, key: str) -> set[str]:
            return redis_data.get(key, set())

        async def expire(self, key: str, ttl: int) -> None:
            pass  # No-op for in-memory mock

        async def delete(self, key: str) -> None:
            redis_data.pop(key, None)

        async def get(self, key: str) -> str | None:
            return redis_hash.get(key)

        async def set(self, key: str, value: str, ex: int | None = None):
            redis_hash[key] = value

        async def keys(self, pattern: str):
            import re
            regex = re.escape(pattern).replace(r"\*", ".*")
            return [k for k in redis_data if re.match(regex, k)]

        async def exists(self, key: str) -> bool:
            return key in redis_data or key in redis_hash

        async def aclose(self) -> None:
            pass

    mock_instance = MockRedisInstance()

    with patch("app.auth.redis_client.get_redis", return_value=mock_instance):
        yield mock_instance


class TestCreateRefreshToken:
    """create_refresh_token must produce a 7-day token with 'refresh' purpose."""

    def test_create_refresh_token_valid_jwt(self):
        """A refresh token is a valid JWT with 'refresh' purpose."""
        user_id = "test-user-123"
        token = create_refresh_token(user_id)
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == user_id
        assert payload["purpose"] == "refresh"

    def test_create_refresh_token_7_day_expiry(self):
        """Refresh token expires in approximately 7 days."""
        user_id = "test-user-456"
        token = create_refresh_token(user_id)
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        diff = exp - iat
        assert timedelta(days=6, hours=23) <= diff <= timedelta(days=7, hours=1)

    def test_refresh_token_different_purpose_from_access(self):
        """Refresh token has purpose='refresh', access token has no purpose."""
        user_id = "test-user-789"
        refresh = create_refresh_token(user_id)
        access = create_access_token(user_id)
        refresh_payload = jwt.decode(refresh, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        access_payload = jwt.decode(access, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert refresh_payload.get("purpose") == "refresh"
        assert access_payload.get("purpose") is None


class TestRefreshEndpointWithRotation:
    """POST /auth/refresh must rotate tokens and blacklist old ones."""

    async def test_refresh_returns_new_tokens(
        self, async_client: AsyncClient, test_user, mock_redis
    ):
        """A valid refresh token returns a new access+refresh pair."""
        refresh = create_refresh_token(subject=test_user.id)
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert len(body["refresh_token"]) > 0  # Has a refresh token
        assert len(body["access_token"]) > 0  # Has an access token

    async def test_refresh_blacklists_old_token(
        self, async_client: AsyncClient, test_user, mock_redis
    ):
        """Old refresh token is blacklisted after refresh."""
        refresh = create_refresh_token(subject=test_user.id)
        await async_client.post("/api/auth/refresh", json={"refresh_token": refresh})
        # The old token should now be in the blacklist
        blacklist_key = f"refresh_blacklist:{test_user.id}"
        assert await mock_redis.sismember(blacklist_key, refresh)

    async def test_refresh_with_invalid_token_returns_401(
        self, async_client: AsyncClient
    ):
        """Invalid or expired refresh token returns 401."""
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid-refresh-token"},
        )
        assert response.status_code == 401

    async def test_refresh_sets_new_cookie(
        self, async_client: AsyncClient, test_user, mock_redis
    ):
        """Refresh endpoint also sets new access_token cookie."""
        refresh = create_refresh_token(subject=test_user.id)
        response = await async_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie

    async def test_cannot_reuse_blacklisted_token(
        self, async_client: AsyncClient, test_user, mock_redis
    ):
        """Reusing a blacklisted refresh token returns 401."""
        refresh = create_refresh_token(subject=test_user.id)
        # First use — valid
        resp1 = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert resp1.status_code == 200
        # Second use — should be blacklisted
        resp2 = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert resp2.status_code == 401


# ---------------------------------------------------------------------------
# Task 2.4: Logout
# ---------------------------------------------------------------------------


class TestLogout:
    """POST /auth/logout must blacklist the refresh token and clear cookie."""

    async def test_logout_returns_200(self, async_client: AsyncClient, test_user, mock_redis):
        """Logout with valid tokens returns 200."""
        token = create_access_token(subject=test_user.id)
        refresh = create_refresh_token(subject=test_user.id)
        response = await async_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            json={"refresh_token": refresh},
        )
        assert response.status_code == 200

    async def test_logout_blacklists_refresh(
        self, async_client: AsyncClient, test_user, mock_redis
    ):
        """Logout adds the refresh token to the blacklist."""
        token = create_access_token(subject=test_user.id)
        refresh = create_refresh_token(subject=test_user.id)
        await async_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            json={"refresh_token": refresh},
        )
        blacklist_key = f"refresh_blacklist:{test_user.id}"
        assert await mock_redis.sismember(blacklist_key, refresh)

    async def test_logout_clears_cookie(
        self, async_client: AsyncClient, test_user, mock_redis
    ):
        """Logout sets cookie with empty value and max-age=0."""
        token = create_access_token(subject=test_user.id)
        refresh = create_refresh_token(subject=test_user.id)
        response = await async_client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            json={"refresh_token": refresh},
        )
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()

    async def test_logout_without_token_returns_401(
        self, async_client: AsyncClient
    ):
        """Logout without auth returns 401."""
        response = await async_client.post(
            "/api/auth/logout",
            json={"refresh_token": "some-token"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Task 2.5: Theft detection
# ---------------------------------------------------------------------------


class TestTheftDetection:
    """Reusing a blacklisted refresh token must trigger theft detection."""

    async def test_reuse_after_refresh_triggers_theft_clear(
        self, async_client: AsyncClient, test_user, mock_redis
    ):
        """Reusing a blacklisted refresh token deletes ALL blacklist entries for user."""
        refresh = create_refresh_token(subject=test_user.id)

        # Use refresh once — gets rotated
        resp1 = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert resp1.status_code == 200
        body1 = resp1.json()
        new_refresh = body1["refresh_token"]

        # Use the NEW rotated refresh to populate a second blacklist entry
        resp2 = await async_client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
        assert resp2.status_code == 200

        # Now reuse the OLD (blacklisted) refresh — theft detected
        resp3 = await async_client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert resp3.status_code == 401

        # The entire user's blacklist should be deleted
        blacklist_key = f"refresh_blacklist:{test_user.id}"
        members = await mock_redis.smembers(blacklist_key)
        assert len(members) == 0

    async def test_theft_logs_warning(
        self, async_client: AsyncClient, test_user, mock_redis, caplog
    ):
        """Theft detection logs a warning."""
        import logging
        refresh = create_refresh_token(subject=test_user.id)

        await async_client.post("/api/auth/refresh", json={"refresh_token": refresh})
        caplog.clear()
        with caplog.at_level(logging.WARNING):
            await async_client.post("/api/auth/refresh", json={"refresh_token": refresh})
        assert any("theft" in msg.lower() for msg in caplog.messages)


# ---------------------------------------------------------------------------
# Task 2.8: Additional auth tests
# ---------------------------------------------------------------------------


class TestAccessTokenExpiry:
    """Access tokens should have ~15 min expiry."""

    def test_access_token_15_min_expiry(self):
        """Access token expires in approximately 15 minutes."""
        token = create_access_token(subject="test-user")
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        diff = exp - iat
        assert timedelta(minutes=14) <= diff <= timedelta(minutes=16)


class TestCookieDualAuth:
    """Both cookie and Bearer header must work simultaneously."""

    async def test_bearer_only_still_works(self, async_client: AsyncClient, test_user):
        """Old clients using only Bearer token still work."""
        token = create_access_token(subject=test_user.id)
        response = await async_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == test_user.id
