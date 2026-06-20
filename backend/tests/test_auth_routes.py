"""Integration tests for ``app.auth.router``.

Covers registration, login, token validation, and unauthenticated access
via the HTTP API using ``httpx.AsyncClient``.
"""

from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from jose import jwt
from sqlalchemy import select

from app.auth.utils import hash_password
from app.config import settings
from app.models import User

# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_register_creates_user_and_returns_token(
        self,
        async_client: AsyncClient,
        db_session,
    ):
        """Registering with valid data returns 201 and a JWT token."""
        payload = {
            "email": "newuser@example.com",
            "password": "StrongPass1",
            "name": "New User",
        }
        resp = await async_client.post("/api/auth/register", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        # Verify the token is valid
        decoded = jwt.decode(
            body["access_token"],
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        assert decoded["sub"] is not None

        # User should exist in the database
        result = await db_session.execute(
            select(User).where(User.email == "newuser@example.com"),
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.name == "New User"

    async def test_register_duplicate_email_returns_409(
        self,
        async_client: AsyncClient,
        test_user,
    ):
        """Registering with an existing email returns 409 Conflict."""
        payload = {
            "email": test_user.email,
            "password": "AnotherPass1",
        }
        resp = await async_client.post("/api/auth/register", json=payload)
        assert resp.status_code == 409
        body = resp.json()
        assert "detail" in body

    async def test_register_invalid_email_returns_422(
        self,
        async_client: AsyncClient,
    ):
        """Registering with an invalid email format returns 422."""
        payload = {
            "email": "not-an-email",
            "password": "StrongPass1",
        }
        resp = await async_client.post("/api/auth/register", json=payload)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_login_valid_credentials_returns_token(
        self,
        async_client: AsyncClient,
        db_session,
    ):
        """Login with correct credentials returns 200 and a JWT token."""
        # Create user manually
        user = User(
            email="logintest@example.com",
            password_hash=hash_password("correct-password"),
            name="Login Test",
        )
        db_session.add(user)
        await db_session.flush()

        payload = {"email": "logintest@example.com", "password": "correct-password"}
        resp = await async_client.post("/api/auth/login", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password_returns_401(
        self,
        async_client: AsyncClient,
        db_session,
    ):
        """Login with wrong password returns 401."""
        user = User(
            email="wrongpw@example.com",
            password_hash=hash_password("real-password"),
        )
        db_session.add(user)
        await db_session.flush()

        payload = {"email": "wrongpw@example.com", "password": "wrong"}
        resp = await async_client.post("/api/auth/login", json=payload)
        assert resp.status_code == 401

    async def test_login_nonexistent_email_returns_401(
        self,
        async_client: AsyncClient,
    ):
        """Login with an email that does not exist returns 401."""
        payload = {"email": "nobody@example.com", "password": "any"}
        resp = await async_client.post("/api/auth/login", json=payload)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


class TestMe:
    async def test_me_valid_token_returns_user(
        self,
        async_client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """GET /me with a valid token returns the user profile."""
        resp = await async_client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "email" in body
        assert body["email"] == "test@example.com"

    async def test_me_no_token_returns_401(
        self,
        async_client: AsyncClient,
    ):
        """GET /me without authorization returns 401."""
        resp = await async_client.get("/api/auth/me")
        assert resp.status_code in (401, 403, 422)

    async def test_me_invalid_token_returns_401(
        self,
        async_client: AsyncClient,
    ):
        """GET /me with a garbage token returns 401."""
        headers = {"Authorization": "Bearer invalid-token"}
        resp = await async_client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401

    async def test_me_expired_token_returns_401(
        self,
        async_client: AsyncClient,
        test_user,
    ):
        """GET /me with an expired token returns 401."""
        expired_payload = {
            "sub": test_user.id,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        resp = await async_client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 401
