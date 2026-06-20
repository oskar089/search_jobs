"""E2E tests for the full auth → profile user flow.

Tests register → login → GET /auth/me → PUT /profiles → GET /profiles →
PUT /profiles (update) → JWT guard for unauthenticated requests.

This is the critical user journey. Every assertion validates a real endpoint.
"""

from uuid import uuid4

from httpx import AsyncClient


class TestAuthProfileE2E:
    """Complete user session: register, authenticate, create/update profile."""

    async def test_full_flow(
        self,
        async_client: AsyncClient,
        db_session,  # noqa: ARG002 — ensures DB session wiring
    ) -> None:
        """Register a new user, verify auth, create/read/update profile, check guard.

        This test simulates a real user session end-to-end without relying on
        the ``test_user`` or ``auth_headers`` fixtures — it creates a fresh
        user via the register endpoint and uses that token for all subsequent
        requests.
        """
        unique_slug = uuid4().hex[:8]
        email = f"e2e_{unique_slug}@example.com"

        # ── 1. Register a new user ────────────────────────────────────────
        register_payload = {
            "email": email,
            "password": "E2eTest123",
            "name": "E2E User",
        }
        resp = await async_client.post("/api/auth/register", json=register_payload)
        assert resp.status_code == 201, f"Register failed: {resp.text}"
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        token = body["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # ── 2. GET /auth/me — verify the token works ──────────────────────
        resp = await async_client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200, f"GET /me failed: {resp.text}"
        assert resp.json()["email"] == email

        # ── 3. PUT /profiles — create a profile (upsert) ──────────────────
        create_payload = {
            "experience_level": "senior",
            "target_roles": ["backend", "devops"],
            "tech_stack": ["python", "fastapi"],
        }
        resp = await async_client.put(
            "/api/profiles",
            json=create_payload,
            headers=headers,
        )
        assert resp.status_code == 200, f"Create profile failed: {resp.text}"
        profile = resp.json()
        assert profile["experience_level"] == "senior"
        assert profile["target_roles"] == ["backend", "devops"]
        assert profile["tech_stack"] == ["python", "fastapi"]
        assert profile["is_active"] is True

        # ── 4. GET /profiles — read the profile back ──────────────────────
        resp = await async_client.get("/api/profiles", headers=headers)
        assert resp.status_code == 200, f"GET profile failed: {resp.text}"
        fetched = resp.json()
        assert fetched["experience_level"] == "senior"
        assert fetched["target_roles"] == ["backend", "devops"]
        assert fetched["tech_stack"] == ["python", "fastapi"]

        # ── 5. PUT /profiles — partial update ─────────────────────────────
        update_payload: dict = {"experience_level": "mid", "max_salary": 90000}
        resp = await async_client.put(
            "/api/profiles",
            json=update_payload,
            headers=headers,
        )
        assert resp.status_code == 200, f"Update profile failed: {resp.text}"
        updated = resp.json()
        # Updated fields
        assert updated["experience_level"] == "mid"
        assert updated["max_salary"] == 90000
        # Unchanged fields are preserved
        assert updated["target_roles"] == ["backend", "devops"]
        assert updated["tech_stack"] == ["python", "fastapi"]

        # ── 6. JWT guard — unauthenticated requests are rejected ──────────
        resp = await async_client.get("/api/auth/me")
        assert resp.status_code in (401, 403, 422)

        resp = await async_client.get("/api/profiles")
        assert resp.status_code in (401, 403, 422)

        resp = await async_client.put(
            "/api/profiles",
            json={"experience_level": "junior"},
        )
        assert resp.status_code in (401, 403, 422)
