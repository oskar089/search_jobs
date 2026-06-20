"""Integration tests for ``app.profiles.router``.

Covers GET and PUT profile endpoints: CRUD, validation, and
unauthenticated rejection via the HTTP API.
"""

from httpx import AsyncClient

from app.models import Profile

# ---------------------------------------------------------------------------
# GET /api/profiles
# ---------------------------------------------------------------------------


class TestGetProfile:
    async def test_get_profile_when_exists(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers,
    ):
        """GET /profiles returns the user's profile when it exists."""
        profile = Profile(
            user_id=test_user.id,
            experience_level="senior",
            target_roles=["backend"],
            tech_stack=["python"],
        )
        db_session.add(profile)
        await db_session.flush()

        resp = await async_client.get("/api/profiles", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == test_user.id
        assert body["experience_level"] == "senior"
        assert body["target_roles"] == ["backend"]
        assert body["tech_stack"] == ["python"]
        assert body["is_active"] is True
        assert "id" in body

    async def test_get_profile_not_found(
        self,
        async_client: AsyncClient,
        auth_headers,
    ):
        """GET /profiles returns 404 when no profile exists for the user."""
        resp = await async_client.get("/api/profiles", headers=auth_headers)
        assert resp.status_code == 404

    async def test_get_profile_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """GET /profiles without auth returns 401/422 (422 = missing required header)."""
        resp = await async_client.get("/api/profiles")
        # FastAPI returns 422 when a required Header param is missing
        assert resp.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# PUT /api/profiles — create
# ---------------------------------------------------------------------------


class TestPutProfileCreate:
    async def test_put_profile_create_minimal(
        self,
        async_client: AsyncClient,
        auth_headers,
        test_user,
    ):
        """PUT /profiles creates a profile with just experience_level."""
        payload = {"experience_level": "junior"}
        resp = await async_client.put("/api/profiles", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == test_user.id
        assert body["experience_level"] == "junior"
        assert body["target_roles"] == []
        assert body["tech_stack"] == []
        assert body["is_active"] is True

    async def test_put_profile_create_full(
        self,
        async_client: AsyncClient,
        auth_headers,
        test_user,
    ):
        """PUT /profiles with all fields stores them correctly."""
        payload = {
            "experience_level": "senior",
            "target_roles": ["backend", "devops"],
            "tech_stack": ["python", "fastapi"],
            "min_salary": 80000,
            "max_salary": 150000,
            "locations": ["Remote"],
            "remote_only": True,
            "languages": ["en", "es"],
            "is_active": True,
        }
        resp = await async_client.put("/api/profiles", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["experience_level"] == "senior"
        assert body["min_salary"] == 80000
        assert body["max_salary"] == 150000
        assert body["remote_only"] is True
        assert body["languages"] == ["en", "es"]

    async def test_put_profile_create_missing_experience_level_returns_422(
        self,
        async_client: AsyncClient,
        auth_headers,
    ):
        """PUT /profiles without experience_level on create returns 422."""
        payload = {"target_roles": ["engineer"]}
        resp = await async_client.put("/api/profiles", json=payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_put_profile_create_unauthenticated(
        self,
        async_client: AsyncClient,
    ):
        """PUT /profiles without auth returns 401/422 (422 = missing required header)."""
        payload = {"experience_level": "senior"}
        resp = await async_client.put("/api/profiles", json=payload)
        # FastAPI returns 422 when a required Header param is missing
        assert resp.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# PUT /api/profiles — update
# ---------------------------------------------------------------------------


class TestPutProfileUpdate:
    async def test_put_profile_update_partial(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers,
    ):
        """PUT /profiles on an existing profile updates only provided fields."""
        profile = Profile(
            user_id=test_user.id,
            experience_level="junior",
            min_salary=50000,
            max_salary=80000,
        )
        db_session.add(profile)
        await db_session.flush()

        payload = {"experience_level": "mid", "max_salary": 100000}
        resp = await async_client.put("/api/profiles", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["experience_level"] == "mid"
        assert body["max_salary"] == 100000
        assert body["min_salary"] == 50000  # unchanged

    async def test_put_profile_update_clears_optional_field(
        self,
        async_client: AsyncClient,
        db_session,
        test_user,
        auth_headers,
    ):
        """PUT /profiles can set an optional field to ``null``."""
        profile = Profile(
            user_id=test_user.id,
            experience_level="senior",
            min_salary=100000,
        )
        db_session.add(profile)
        await db_session.flush()

        payload = {"min_salary": None}
        resp = await async_client.put("/api/profiles", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["min_salary"] is None
