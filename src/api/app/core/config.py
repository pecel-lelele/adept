"""Application settings, read from environment variables and the root .env."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Adept API"
    # production: refuse to start without the secrets a shared deployment needs.
    app_env: Literal["development", "production"] = "development"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    # Retain the deployed configuration name; authentication always uses signed local accounts.
    auth_mode: Literal["demo"] = "demo"
    database_url: str = "postgresql://adept:adept@127.0.0.1:5433/adept"
    # Largest number of pooled database connections per API process (app.core.db).
    db_pool_max: int = 10
    cors_origins: str = Field(default="http://localhost:3000")
    web_origin: str = ""
    log_level: str = "INFO"
    llm_provider: str = "none"
    llm_model: str = ""
    llm_api_key: str = ""
    # OpenAI-compatible endpoint (Replit AI Integrations sets its own; see core/llm/provider.py).
    llm_base_url: str = ""
    llm_timeout_s: float = 20.0
    # Comma-separated models tried when LLM_MODEL is rate-limited or failing (same provider).
    llm_fallback_model: str = ""
    # Separate credentials: a fallback provider must never receive the primary provider's key.
    runpod_api_key: str = ""
    gemini_api_key: str = ""
    llm_fallback_provider: str = ""
    llm_fallback_base_url: str = ""
    llm_fallback_api_key: str = ""
    # Text embeddings for cosine-similarity skill matching (app.core.embeddings). "gemini" uses
    # GEMINI_API_KEY; "none" turns suggestions off and keeps exact catalogue matching only.
    embeddings_provider: Literal["gemini", "none"] = "none"
    embeddings_model: str = "gemini-embedding-001"
    embeddings_timeout_s: float = 15.0
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
    trusted_proxy_hops: int = Field(default=0, ge=0, le=32)
    proxy_client_ip_mode: Literal["trusted", "best-effort"] = "best-effort"
    # Minimum consenting, completed-intake members before showing team gap aggregates.
    org_min_cohort: int = Field(default=3, ge=1)
    # Seconds the public impact summary is reused before it is recomputed (0 = every request).
    impact_summary_ttl_s: int = Field(default=120, ge=0, le=3600)
    # --- storage ---
    # postgres (default): every account, profile, organisation, plan, progress record and
    # rate-limit counter lives in DATABASE_URL, so nothing a user enters is kept only in one
    # process. csv: in-memory stores plus seed files, for the automated tests only.
    m3_backend: Literal["csv", "postgres"] = "postgres"
    # Signs session tokens for local accounts. Required in any shared deployment.
    session_secret: str = ""
    # Test harness only (tests/conftest.py): accept a raw user id in X-Demo-User, and act as
    # this user when no header is sent. Never enable outside the test suite.
    auth_raw_user_ids: bool = False
    auth_default_user: str = ""
    # Secret for POST .../sync endpoints that refresh live data; empty = sync disabled.
    sync_token: str = ""
    # Scheduler-only credential; never accepted as a user session or returned to browsers.
    data_refresh_token: str = Field(default="", repr=False)
    trends_stale_days: int = Field(default=10, ge=1, le=365)
    trends_refresh_cooldown_minutes: int = Field(default=10, ge=1, le=1440)
    # After a failed trends step, non-admin refresh checks skip the paid MiniLM step this long.
    trends_failure_backoff_minutes: int = Field(default=60, ge=1, le=10080)
    # Stable, operator-provisioned account IDs; self-asserted signup email grants no access.
    admin_user_ids: str = ""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        if os.environ.get("APP_ENV", "").strip().lower() == "production":
            return init_settings, env_settings, file_secret_settings
        return init_settings, env_settings, dotenv_settings, file_secret_settings

    @field_validator("session_secret")
    @classmethod
    def _reject_public_session_secret(cls, value: str) -> str:
        if value.strip() == "change-me-to-a-long-random-string-of-32-plus-chars":
            raise ValueError("Generate a private SESSION_SECRET; the public example key is unsafe.")
        return value

    @field_validator("database_url")
    @classmethod
    def _prefer_ipv4_loopback(cls, value: str) -> str:
        """Docker publishes PostgreSQL on 127.0.0.1 only. On Windows `localhost` resolves to
        ::1 first, so every connection waited out the full connect timeout (2 s) before
        falling back, which timed out trend reads and made matching return 503."""
        return value.replace("@localhost:", "@127.0.0.1:").replace("@localhost/", "@127.0.0.1/")

    def deployment_problems(self) -> tuple[list[str], list[str]]:
        """(errors, warnings) for this configuration. Errors stop a production start."""
        errors: list[str] = []
        warnings: list[str] = []
        if self.app_env == "production":
            if len(self.session_secret) < 32:
                errors.append("SESSION_SECRET must be set to a random value of 32+ characters.")
            if "*" in self.cors_origin_list:
                errors.append("CORS_ORIGINS must list exact origins, not '*'.")
            if self.auth_raw_user_ids or self.auth_default_user:
                errors.append("AUTH_RAW_USER_IDS / AUTH_DEFAULT_USER are test-only settings.")
            if self.m3_backend != "postgres":
                errors.append("M3_BACKEND must be postgres; csv is for automated tests only.")
            if not self.web_origin.strip():
                errors.append("WEB_ORIGIN must be set to the app's exact public origin.")
            if not self.proxy_shared_secret.strip():
                errors.append("PROXY_SHARED_SECRET is required on both web and API services.")
            if self.proxy_client_ip_mode == "trusted" and self.trusted_proxy_hops == 0:
                errors.append("TRUSTED_PROXY_HOPS must be a verified positive proxy count.")
            if self.proxy_client_ip_mode == "best-effort":
                warnings.append(
                    "PROXY_CLIENT_IP_MODE=best-effort: anonymous limits use a verified "
                    "forwarded suffix only with positive TRUSTED_PROXY_HOPS, otherwise "
                    "the direct peer (which may share an anonymous rate bucket). "
                    "Authenticated limits use verified session IDs."
                )
        return errors, warnings

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
