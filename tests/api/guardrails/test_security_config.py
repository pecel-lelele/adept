"""Security-relevant configuration that is easy to regress (review finding P1)."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import routes
from app.core.config import Settings
from app.main import create_app

ROOT = Path(__file__).resolve().parents[3]


def test_postgres_port_is_bound_to_localhost_by_default() -> None:
    compose = (ROOT / "docker-compose.db.yml").read_text(encoding="utf-8")
    ports = re.findall(r'-\s*"([^"]+):5432"', compose)
    assert ports, "db service must publish 5432"
    for mapping in ports:
        assert mapping.startswith("${POSTGRES_BIND:-127.0.0.1}:"), mapping


def test_env_example_documents_bind_address() -> None:
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "POSTGRES_BIND=127.0.0.1" in env


def test_production_starts_and_serves_with_zero_proxy_hops(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "0")
    settings = Settings(
        _env_file=None,
        session_secret="synthetic-session-secret-32-characters",
        proxy_shared_secret="synthetic-proxy-secret",
        proxy_client_ip_mode="best-effort",
        m3_backend="postgres",
        web_origin="https://adept.example.test",
        auth_raw_user_ids=False,
        auth_default_user="",
    )
    assert settings.app_env == "production" and settings.trusted_proxy_hops == 0
    assert settings.deployment_problems()[0] == []
    assert settings.deployment_problems()[1]
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    monkeypatch.setattr(routes, "database_status", lambda: "ok")
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/health").status_code == 200
    trusted = settings.model_copy(update={"proxy_client_ip_mode": "trusted"})
    assert any("TRUSTED_PROXY_HOPS" in error for error in trusted.deployment_problems()[0])
