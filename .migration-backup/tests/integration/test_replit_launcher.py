"""Production startup must fail visibly and never leave a half-running container."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts import replit


@pytest.fixture
def deployment_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    env = {
        "DATABASE_URL": "postgresql://example:private@db.example.test/adept",
        "SESSION_SECRET": "synthetic-test-session-secret-32-characters",
        "WEB_ORIGIN": "https://adept.example.test",
    }
    for key in ["DATABASE_URL", "SESSION_SECRET", "WEB_ORIGIN", "PORT", "CORS_ORIGINS"]:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env


def test_runtime_uses_private_api_and_production_mode(deployment_env: dict[str, str]) -> None:
    env = replit.production_env(dict(deployment_env, API_URL="https://stale.example.test"))
    assert env["APP_ENV"] == env["NODE_ENV"] == "production"
    assert env["API_URL"] == "http://127.0.0.1:8000"
    assert env["HOSTNAME"] == "0.0.0.0"
    assert env["PORT"] == "3000"
    assert env["CORS_ORIGINS"] == deployment_env["WEB_ORIGIN"]
    assert env["DATABASE_URL"] == deployment_env["DATABASE_URL"]
    assert "APP_ENV" not in deployment_env


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("DATABASE_URL", "", "DATABASE_URL"),
        ("SESSION_SECRET", "short-private-secret", "SESSION_SECRET"),
        ("WEB_ORIGIN", "", "WEB_ORIGIN"),
        ("WEB_ORIGIN", "https://example.test/", "WEB_ORIGIN"),
        ("WEB_ORIGIN", "https://[invalid", "WEB_ORIGIN"),
        ("PORT", "invalid", "PORT"),
        ("PORT", "8000", "PORT"),
        ("PORT", "80", "PORT"),
    ],
)
def test_invalid_configuration_is_actionable_and_sanitized(
    deployment_env: dict[str, str], key: str, value: str, message: str
) -> None:
    with pytest.raises(replit.DeploymentError, match=message) as exc:
        replit.production_env(dict(deployment_env, **{key: value}))
    assert "private" not in str(exc.value)


def test_standalone_includes_public_assets_and_css(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    standalone = tmp_path / ".next" / "standalone"
    standalone.mkdir(parents=True)
    (standalone / "server.js").write_text("// built server")
    (tmp_path / "public").mkdir()
    (tmp_path / "public" / "mascot.svg").write_text("<svg/>")
    (tmp_path / ".next" / "static").mkdir()
    (tmp_path / ".next" / "static" / "app.css").write_text("body{}")
    monkeypatch.setattr(replit, "WEB", tmp_path)
    monkeypatch.setattr(replit, "STANDALONE", standalone)
    replit.prepare_standalone()
    assert (standalone / "public" / "mascot.svg").is_file()
    assert (standalone / ".next" / "static" / "app.css").is_file()


def test_existing_replit_workspace_keeps_its_public_port(
    tmp_path: Path, deployment_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".replit").write_text("[[ports]]\nlocalPort = 5000\nexternalPort = 80\n")
    monkeypatch.setattr(replit, "ROOT", tmp_path)
    assert replit.production_env(deployment_env)["PORT"] == "5000"


def test_api_failure_stops_container_without_starting_web(
    deployment_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(replit, "doctor", lambda: {"status": "ready"})
    api = MagicMock()
    api.poll.return_value = 1
    popen = MagicMock(return_value=api)
    monkeypatch.setattr(replit.subprocess, "Popen", popen)
    with pytest.raises(replit.DeploymentError, match="FastAPI exited"):
        replit.start()
    assert popen.call_count == 1
    api.wait.assert_called_once()


def test_web_failure_terminates_api(
    deployment_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(replit, "doctor", lambda: {"status": "ready"})
    monkeypatch.setattr(replit, "wait_for_api", lambda _: None)
    api, web = MagicMock(), MagicMock()
    api.poll.return_value = None
    web.poll.return_value = 2
    monkeypatch.setattr(replit.subprocess, "Popen", MagicMock(side_effect=[api, web]))
    assert replit.start() == 2
    api.terminate.assert_called_once()
    api.wait.assert_called_once()


def test_api_wait_rejects_unavailable_database(monkeypatch: pytest.MonkeyPatch) -> None:
    process = MagicMock()
    process.poll.return_value = None
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(
        {"status": "ok", "database": "unavailable"}
    ).encode()
    monkeypatch.setattr(replit.urllib.request, "urlopen", lambda *args, **kwargs: response)
    monkeypatch.setattr(replit.time, "monotonic", MagicMock(side_effect=[0, 0, 50]))
    monkeypatch.setattr(replit.time, "sleep", lambda _: None)
    with pytest.raises(replit.DeploymentError, match="DATABASE_URL"):
        replit.wait_for_api(process)
