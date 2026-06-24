from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Search Jobs"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api"
    app_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Database
    database_url: str = (
        "postgresql+asyncpg://neondb_owner:npg_jM9hvZynakK0@"
        "ep-odd-block-ad1a5lon.c-2.us-east-1.aws.neon.tech/neondb?ssl=require"
    )

    # Auth
    jwt_secret: str = "change-me-to-a-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expires_in_minutes: int = 10080  # 7 days

    # Redis (Celery)
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    llm_api_key: str = ""
    llm_model: str = "gpt-4"
    llm_api_url: str = "https://api.openai.com/v1/chat/completions"

    # Matching
    match_threshold: int = 75

    # LinkedIn Import (free Playwright scraper)
    linkedin_api_key: str = ""   # Leave empty to use free Playwright scraper
    linkedin_api_url: str = "https://api.scrapin.io"
    linkedin_email: str = ""      # Optional: for Playwright auto-login
    linkedin_password: str = ""   # Optional: for Playwright auto-login

    # File Uploads
    upload_dir: str = "uploads/cv"

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@searchjobs.app"


settings = Settings()
