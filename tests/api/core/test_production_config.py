"""Production configuration: no developer .env, a real store, an exact origin, scoped keys."""

from pathlib import Path

import pytest

from app.core import config
from app.core.config import Settings
from app.core.llm import provider

GOOD = {
    "app_env": "production",
    "session_secret": "synthetic-session-secret-with-32-characters",
    "proxy_shared_secret": "synthetic-proxy-secret",
    "m3_backend": "postgres",
    "web_origin": "https://adept.example.test",
    "auth_raw_user_ids": False,
    "auth_default_user": "",
}


def test_a_complete_production_configuration_has_no_errors() -> None:
    assert Settings(_env_file=None, **GOOD).deployment_problems()[0] == []


@pytest.mark.parametrize(
    ("override", "message"),
    [({"m3_backend": "csv"}, "M3_BACKEND"), ({"web_origin": ""}, "WEB_ORIGIN")],
)
def test_production_rejects_test_storage_and_a_missing_origin(
    override: dict[str, str], message: str
) -> None:
    errors, _ = Settings(_env_file=None, **{**GOOD, **override}).deployment_problems()
    assert any(message in error for error in errors)


def test_development_does_not_require_production_settings() -> None:
    settings = Settings(_env_file=None, app_env="development", m3_backend="csv", web_origin="")
    assert settings.deployment_problems()[0] == []


def test_production_never_reads_the_developer_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("LOG_LEVEL=FROM_DOTENV\n", encoding="utf-8")
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.setattr(Settings, "model_config", {**Settings.model_config, "env_file": env_file})
    monkeypatch.setenv("APP_ENV", "development")
    assert Settings().log_level == "FROM_DOTENV"
    monkeypatch.setenv("APP_ENV", "production")
    assert Settings().log_level == "INFO"
    assert config.REPO_ROOT.is_dir()


@pytest.mark.parametrize("name", ["runpod", "gemini"])
def test_runpod_and_gemini_never_use_the_generic_key(name: str) -> None:
    settings = Settings(
        _env_file=None,
        llm_provider=name,
        llm_model="synthetic-model",
        llm_base_url="https://llm.example.test/v1",
        llm_api_key="generic",
    )
    built = provider.build_provider(settings)
    assert isinstance(built, provider.OpenAICompatibleProvider)
    assert "Authorization" not in built._headers
    own = {"runpod_api_key": "runpod-only"} if name == "runpod" else {"gemini_api_key": "g-only"}
    scoped = provider.build_provider(settings.model_copy(update=own))
    assert isinstance(scoped, provider.OpenAICompatibleProvider)
    assert scoped._headers["Authorization"] == f"Bearer {next(iter(own.values()))}"


def test_openai_compatible_providers_keep_the_generic_key() -> None:
    settings = Settings(
        _env_file=None, llm_provider="openrouter", llm_model="synthetic", llm_api_key="generic"
    )
    built = provider.build_provider(settings)
    assert isinstance(built, provider.OpenAICompatibleProvider)
    assert built._headers["Authorization"] == "Bearer generic"
