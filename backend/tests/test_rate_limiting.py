"""Tests for rate limiting on auth endpoints.

Requires slowapi middleware to be wired (Task 3.1) and
@limiter.limit decorators on login (5/min) and register (10/min) (Task 3.2).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestRateLimiting:
    """Auth endpoints must enforce per-IP rate limits."""

    async def test_login_rate_limited_after_5_attempts(
        self, async_client: AsyncClient, test_user
    ):
        """Login returns 429 after 5 rapid requests from the same IP."""
        for i in range(5):
            resp = await async_client.post(
                "/api/auth/login",
                json={"email": test_user.email, "password": "wrongpass"},
            )
            # First 5 should be 401 (wrong password), not rate limited
            assert resp.status_code == 401, f"Attempt {i+1} expected 401, got {resp.status_code}"

        # 6th request should be rate limited
        resp = await async_client.post(
            "/api/auth/login",
            json={"email": test_user.email, "password": "wrongpass"},
        )
        assert resp.status_code == 429

    async def test_register_rate_limited_after_10_attempts(
        self, async_client: AsyncClient
    ):
        """Register returns 429 after 10 rapid requests from the same IP."""
        for i in range(10):
            resp = await async_client.post(
                "/api/auth/register",
                json={
                    "email": f"test-{i}@example.com",
                    "password": "TestPass123",
                    "name": f"User {i}",
                },
            )
            # Some may be 201 (success) or 409 (email taken), not rate limited
            assert resp.status_code in (201, 409), f"Attempt {i+1} expected 201/409, got {resp.status_code}"

        # 11th request should be rate limited
        resp = await async_client.post(
            "/api/auth/register",
            json={
                "email": "final-test@example.com",
                "password": "TestPass123",
                "name": "Final",
            },
        )
        assert resp.status_code == 429

    # Triangulation note: the two tests above (login with 5/min vs register with 10/min)
    # exercise different decoration limits and prove separate counters. A per-IP separation
    # test would need a real HTTP client connection — ASGITransport/httpx test client always
    # reports 127.0.0.1 because there is no actual TCP connection.
