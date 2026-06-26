"""Tests for config.py — Secrets extraction and validation (Phase 1).

Approval tests capture current behavior for refactoring safety.
New behavior tests validate required fields and validate_startup().
"""

from __future__ import annotations

import logging
import re

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Approval tests — behavior that should be PRESERVED after refactoring
# ---------------------------------------------------------------------------


class TestSettingsPreservedBehavior:
    """Behavior that must still work after the refactor."""

    def test_settings_loads_from_env(self, monkeypatch):
        """Settings can be instantiated from environment variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from app.config import Settings

        s = Settings(_env_file=None)
        assert s.database_url == "postgresql+asyncpg://test:test@localhost:5432/test"
        assert s.jwt_secret == "a" * 32
        assert s.redis_url == "redis://localhost:6379/0"

    def test_settings_defaults_are_sensible(self, monkeypatch):
        """Non-sensitive fields retain safe defaults."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from app.config import Settings

        s = Settings(_env_file=None)
        assert s.app_name == "Search Jobs"
        assert s.api_prefix == "/api"
        assert s.jwt_algorithm == "HS256"
        assert s.jwt_expires_in_minutes == 10080
        assert s.upload_dir == "uploads/cv"

    def test_settings_app_env_defaults_development(self, monkeypatch):
        """APP_ENV defaults to 'development'."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from app.config import Settings

        s = Settings(_env_file=None)
        assert s.app_env == "development"


# ---------------------------------------------------------------------------
# New behavior: required fields
# ---------------------------------------------------------------------------


class TestRequiredFields:
    """Required fields must fail at construction when not set."""

    def test_database_url_required(self, monkeypatch):
        """DATABASE_URL must be set — no default allowed."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        # Set other required fields so only DATABASE_URL is missing
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from app.config import Settings

        with pytest.raises(ValidationError) as exc:
            Settings(_env_file=None)
        # pydantic error references the field name (database_url), not the env var
        assert "database_url" in str(exc.value)

    def test_jwt_secret_required(self, monkeypatch):
        """JWT_SECRET must be set — no default allowed."""
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from app.config import Settings

        with pytest.raises(ValidationError) as exc:
            Settings(_env_file=None)
        # pydantic error references the field name (jwt_secret), not the env var
        assert "jwt_secret" in str(exc.value)

    def test_redis_url_required(self, monkeypatch):
        """REDIS_URL must be set — no default allowed."""
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)

        from app.config import Settings

        with pytest.raises(ValidationError) as exc:
            Settings(_env_file=None)
        # pydantic error references the field name (redis_url), not the env var
        assert "redis_url" in str(exc.value)


# ---------------------------------------------------------------------------
# New behavior: validate_startup()
# ---------------------------------------------------------------------------


class TestValidateStartup:
    """validate_startup() validates critical configuration."""

    def make_settings(self, monkeypatch, **overrides) -> object:
        """Helper to create a Settings instance with given overrides."""
        defaults = {
            "database_url": "postgresql+asyncpg://test:test@localhost:5432/test",
            "jwt_secret": "a" * 32,
            "redis_url": "redis://localhost:6379/0",
        }
        defaults.update(overrides)
        for key, value in defaults.items():
            monkeypatch.setenv(key.upper(), value)

        from app.config import Settings

        return Settings(_env_file=None)

    def test_valid_config_passes(self, monkeypatch):
        """validate_startup() passes with valid configuration."""
        s = self.make_settings(monkeypatch)
        # Should not raise
        s.validate_startup()

    def test_short_jwt_secret_rejected(self, monkeypatch):
        """JWT_SECRET shorter than 32 chars is rejected."""
        s = self.make_settings(monkeypatch, jwt_secret="short-key")
        with pytest.raises(ValueError) as exc:
            s.validate_startup()
        assert "32" in str(exc.value) or "JWT_SECRET" in str(exc.value)

    def test_known_default_jwt_secret_rejected(self, monkeypatch):
        """Known default JWT_SECRET values are rejected."""
        s = self.make_settings(monkeypatch, jwt_secret="change-me-to-a-random-secret")
        with pytest.raises(ValueError) as exc:
            s.validate_startup()
        assert "default" in str(exc.value).lower() or "known" in str(exc.value).lower()

    def test_empty_database_url_rejected(self, monkeypatch):
        """Empty DATABASE_URL is rejected by validate_startup()."""
        s = self.make_settings(monkeypatch, database_url="")
        with pytest.raises(ValueError) as exc:
            s.validate_startup()
        assert "DATABASE_URL" in str(exc.value)

    def test_validate_startup_reports_all_errors(self, monkeypatch):
        """validate_startup() reports ALL failures, not just the first."""
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("JWT_SECRET", "short")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from app.config import Settings

        s = Settings(_env_file=None)
        with pytest.raises(ValueError) as exc:
            s.validate_startup()
        msg = str(exc.value)
        # Should mention both DATABASE_URL and JWT_SECRET issues
        assert "DATABASE_URL" in msg
        assert "JWT_SECRET" in msg


# ---------------------------------------------------------------------------
# New behavior: debug mode gated by APP_ENV
# ---------------------------------------------------------------------------


class TestDebugMode:
    """debug mode should be gated by APP_ENV."""

    def test_debug_defaults_to_false_in_production(self, monkeypatch):
        """debug is False when APP_ENV='production'."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("APP_ENV", "production")

        from app.config import Settings

        s = Settings(_env_file=None)
        assert s.debug is False

    def test_debug_is_true_in_development(self, monkeypatch):
        """debug is True when APP_ENV='development'."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("APP_ENV", "development")

        from app.config import Settings

        s = Settings(_env_file=None)
        assert s.debug is True

    def test_debug_is_false_in_staging(self, monkeypatch):
        """debug is False when APP_ENV='staging'."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("APP_ENV", "staging")

        from app.config import Settings

        s = Settings(_env_file=None)
        assert s.debug is False


# ---------------------------------------------------------------------------
# New behavior: Docker secrets support
# ---------------------------------------------------------------------------


class TestDockerSecrets:
    """Docker secrets_dir should be configured."""

    def test_model_config_has_secrets_dir(self, monkeypatch):
        """SettingsConfigDict should include secrets_dir for Docker secrets."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        from app.config import Settings

        s = Settings(_env_file=None)
        # Access the model_config to check for secrets_dir
        config = s.model_config
        assert "/run/secrets" in str(config.get("secrets_dir", ""))


# ---------------------------------------------------------------------------
# New behavior: startup log warnings (main.py)
# ---------------------------------------------------------------------------


class TestStartupWarnings:
    """Non-critical missing configs should log warnings at startup."""

    def test_missing_llm_key_logs_warning(self, monkeypatch, caplog):
        """Missing LLM_API_KEY logs a warning at startup."""
        from app.config import settings
        from app.main import log_non_critical_warnings

        # Clear LLM_API_KEY on the already-instantiated settings
        monkeypatch.setattr(settings, "llm_api_key", "")

        with caplog.at_level(logging.WARNING):
            log_non_critical_warnings()

            llm_warnings = [r.message for r in caplog.records if "LLM_API_KEY" in r.message]
            assert len(llm_warnings) > 0, "Expected a warning about missing LLM_API_KEY"
