"""Application settings, read from environment variables and the root .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Aiversecity Future-Ready Workforce API"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    auth_mode: Literal["demo", "supabase"] = "demo"
    database_url: str = "postgresql://adept:adept@127.0.0.1:5433/adept"
    cors_origins: str = Field(default="http://localhost:3000")
    log_level: str = "INFO"
    llm_provider: str = "none"
    llm_model: str = ""
    llm_api_key: str = ""
    # Largest accepted upload (CV) in bytes; bigger files are rejected with 413.
    max_upload_bytes: int = 5 * 1024 * 1024
    # Largest accepted non-upload request body (JSON) in bytes.
    max_json_bytes: int = 1024 * 1024

    # --- security (F8) ---
    rate_limit_enabled: bool = True
    # Requests per window per client IP for routes without a tighter bucket.
    rate_limit_default: int = 600
    rate_limit_window_s: int = 60
    # Shared secret the web server sends with X-Real-IP so the API can trust it.
    proxy_shared_secret: str = ""
    # --- M3 storage (F5/F6/F8) ---
    # csv: reference data from the seed files, plans/progress/badges/rate limits in memory.
    # postgres: everything in DATABASE_URL (shared by all API instances; survives restarts).
    m3_backend: Literal["csv", "postgres"] = "csv"
    # Secret for POST .../sync endpoints that refresh live data; empty = sync disabled.
    sync_token: str = ""
    # AUTH_MODE=supabase: project JWT secret (HS256) and expected audience.
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
