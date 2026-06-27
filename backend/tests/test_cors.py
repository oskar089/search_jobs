"""Tests for CORS configuration.

Verifies that CORS middleware is configured with restricted methods and headers.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestCORSConfiguration:
    """The CORS middleware must restrict methods and headers."""

    async def test_cors_preflight_returns_restricted_methods(self, async_client: AsyncClient):
        """CORS preflight returns allowed methods (not wildcard)."""
        response = await async_client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        allow_methods = response.headers.get("access-control-allow-methods", "")
        # Should include our restricted methods
        assert "GET" in allow_methods
        assert "POST" in allow_methods
        assert "PUT" in allow_methods
        assert "DELETE" in allow_methods
        assert "PATCH" in allow_methods
        # Should NOT be wildcard
        assert allow_methods != "*"

    async def test_cors_preflight_returns_restricted_headers(self, async_client: AsyncClient):
        """CORS preflight returns the restricted list of allowed headers."""
        response = await async_client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        assert response.status_code == 200
        allow_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "authorization" in allow_headers
        assert "content-type" in allow_headers
        # Should not be wildcard
        assert allow_headers != "*"

    async def test_allowed_origin_gets_cors_headers(self, async_client: AsyncClient):
        """Requests from allowed origin get CORS headers."""
        response = await async_client.get(
            "/api/auth/me",
            headers={"Origin": "http://localhost:5173"},
        )
        # The endpoint may return 401 without auth, but CORS headers should be present
        cors_origin = response.headers.get("access-control-allow-origin", "")
        assert cors_origin == "http://localhost:5173"
