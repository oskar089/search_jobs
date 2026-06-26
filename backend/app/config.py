"""Application configuration via pydantic-settings.

Secrets are loaded from environment variables with Docker secrets fallback
at /run/secrets/. Required fields (DATABASE_URL, JWT_SECRET, REDIS_URL)
have NO defaults — the app fails closed on startup if they're missing.
"""

from __future__ import annotations

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        secrets_dir="/run/secrets",
    )

    # App
    app_name: str = "Search Jobs"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api"
    app_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Database — REQUIRED, no default
    database_url: str

    # Auth — REQUIRED, no default
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expires_in_minutes: int = 15
    refresh_token_expiry_days: int = 7

    # Redis (Celery) — REQUIRED, no default
    redis_url: str

    # LLM
    llm_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"

    # Matching
    match_threshold: int = 75

    # LinkedIn Import (free Playwright scraper)
    linkedin_api_key: str = ""
    linkedin_api_url: str = "https://api.scrapin.io"
    linkedin_email: str = ""
    linkedin_password: str = ""

    # File Uploads
    upload_dir: str = "uploads/cv"

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@searchjobs.app"

    @model_validator(mode="after")
    def _set_debug_from_env(self) -> Settings:
        """Gate debug mode — only True when APP_ENV is 'development'."""
        self.debug = self.app_env == "development"
        return self

    def validate_startup(self) -> None:
        """Validate critical configuration at startup.

        Raises ValueError with ALL failures found, not just the first one.
        Call this during FastAPI startup to fail closed on misconfiguration.
        """
        errors: list[str] = []

        # JWT_SECRET length check (strip to reject whitespace-only values)
        jwt_secret = self.jwt_secret.strip()
        if len(jwt_secret) < 32:
            errors.append(
                "JWT_SECRET is too short. Must be at least 32 characters.",
            )

        # Known default values for JWT_SECRET
        known_defaults = {"change-me-to-a-random-secret"}
        if jwt_secret in known_defaults:
            errors.append(
                "JWT_SECRET is set to a known default value. "
                "Generate a unique secret and set it via JWT_SECRET env var.",
            )

        # DATABASE_URL non-empty check (strip to reject whitespace-only)
        if not self.database_url.strip():
            errors.append("DATABASE_URL must not be empty or whitespace-only.")

        # REDIS_URL non-empty check
        if not self.redis_url.strip():
            errors.append("REDIS_URL must not be empty or whitespace-only.")

        if errors:
            raise ValueError("\n".join(errors))


settings = Settings()
