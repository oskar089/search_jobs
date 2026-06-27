"""Tests for the /health endpoint.

Task 3.8: Probes DB (SELECT 1), Redis (PING), Celery (inspect.ping()).
Returns 200 if all healthy, 503 if any component is unhealthy.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """GET /health must report DB, Redis, and Celery status."""

    @pytest.fixture(autouse=True)
    def mock_all_healthy(self):
        """Patch all three services to appear healthy by default."""
        # Mock DB engine
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value.execute = AsyncMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock()

        # Mock Celery
        mock_celery = MagicMock()
        mock_celery.control.ping.return_value = [{"ok": "pong"}]

        with patch("app.main.engine", mock_engine), \
             patch("app.auth.redis_client.get_redis", return_value=mock_redis), \
             patch("app.main.celery_app", mock_celery):
            yield

    async def test_all_services_healthy(self, async_client: AsyncClient):
        """Returns 200 with all services healthy."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "healthy"
        assert data["redis"] == "healthy"
        assert data["celery"] == "healthy"

    async def test_db_unhealthy_returns_503(self, async_client: AsyncClient):
        """Returns 503 when DB is unreachable."""
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value.execute = AsyncMock(
            side_effect=Exception("DB connection failed")
        )
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("app.main.engine", mock_engine):
            response = await async_client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert data["db"] == "unhealthy"
            # Other services still healthy from auto-use fixture
            assert data["redis"] == "healthy"
            assert data["celery"] == "healthy"

    async def test_redis_unhealthy_returns_503(self, async_client: AsyncClient):
        """Returns 503 when Redis is unreachable."""
        mock_broken_redis = AsyncMock()
        mock_broken_redis.ping = AsyncMock(side_effect=Exception("Redis down"))

        with patch("app.auth.redis_client.get_redis", return_value=mock_broken_redis):
            response = await async_client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert data["redis"] == "unhealthy"
            assert data["db"] == "healthy"
            assert data["celery"] == "healthy"

    async def test_celery_unhealthy_returns_503(self, async_client: AsyncClient):
        """Returns 503 when Celery workers are unreachable."""
        mock_broken_celery = MagicMock()
        mock_broken_celery.control.ping.side_effect = Exception("Celery ping failed")

        with patch("app.main.celery_app", mock_broken_celery):
            response = await async_client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert data["celery"] == "unhealthy"
            assert data["db"] == "healthy"
            assert data["redis"] == "healthy"

    async def test_multiple_failures_reported(self, async_client: AsyncClient):
        """When multiple services fail, all are reported as unhealthy."""
        mock_conn = AsyncMock()
        mock_conn.__aenter__.return_value.execute = AsyncMock(
            side_effect=Exception("DB timeout")
        )
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        mock_broken_redis = AsyncMock()
        mock_broken_redis.ping = AsyncMock(side_effect=Exception("Redis down"))

        with patch("app.main.engine", mock_engine), \
             patch("app.auth.redis_client.get_redis", return_value=mock_broken_redis):
            response = await async_client.get("/health")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert data["db"] == "unhealthy"
            assert data["redis"] == "unhealthy"
            assert data["celery"] == "healthy"
