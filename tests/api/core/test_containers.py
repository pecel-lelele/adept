"""Local containers: loopback ports, lockfile installs, and no implicit migrate/seed."""

import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
DOCKER = ROOT / "src" / "docker"


def _boot() -> ModuleType:
    spec = importlib.util.spec_from_file_location("adept_boot", DOCKER / "boot.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_starting_the_api_never_migrates_or_seeds(monkeypatch: pytest.MonkeyPatch) -> None:
    boot = _boot()
    ran: list[list[str]] = []
    served: list[list[str]] = []
    monkeypatch.setattr(boot.subprocess, "run", lambda cmd, check: ran.append(cmd))
    monkeypatch.setattr(boot.os, "execvp", lambda file, args: served.append(args))
    assert boot.main([]) == 0
    assert ran == [] and served and "uvicorn" in served[0]
    assert boot.main(["migrate"]) == 0
    assert [cmd[1:] for cmd in ran] == [["src/db/migrate.py", "up"], ["src/db/seed.py"]]
    assert len(served) == 1, "the one-off migrate step does not start the API"
    assert boot.main(["seed-everything"]) == 2


@pytest.mark.parametrize("dockerfile", ["api.Dockerfile", "web.Dockerfile"])
def test_dockerfiles_copy_only_paths_that_exist(dockerfile: str) -> None:
    text = (DOCKER / dockerfile).read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("COPY ") or "--from=" in line:
            continue
        for source in line.split()[1:-1]:
            assert (ROOT / source).exists(), f"{dockerfile}: {source} does not exist"


def test_images_install_from_the_committed_lockfiles() -> None:
    api = (DOCKER / "api.Dockerfile").read_text(encoding="utf-8")
    web = (DOCKER / "web.Dockerfile").read_text(encoding="utf-8")
    assert "uv sync --frozen" in api and "requirements.txt" not in api
    assert "pnpm install --frozen-lockfile" in web and "src/web/pnpm-lock.yaml" not in web
    assert re.findall(r"^FROM node:(\d+)", web, re.M) == ["24", "24"]


def _compose(*args: str) -> dict:
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Docker Compose CLI is not installed; no daemon is needed")
    env = {k: v for k, v in os.environ.items() if not k.startswith("COMPOSE_")}
    env["SESSION_SECRET"] = "synthetic-compose-test-secret-32-characters"
    result = subprocess.run(
        [docker, "compose", "--env-file", str(ROOT / ".env.example")]
        + ["-f", str(ROOT / "docker-compose.yml"), *args, "config", "--format", "json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_every_published_port_is_loopback_and_web_uses_node_24() -> None:
    services = _compose("--profile", "setup")["services"]
    assert set(services) == {"db", "api", "web", "migrate"}
    for name, service in services.items():
        for port in service.get("ports", []):
            assert port["host_ip"] == "127.0.0.1", name
    assert services["web"]["image"] == "node:24-alpine"
    assert "--frozen-lockfile" in " ".join(services["web"]["command"])


def test_migration_is_an_explicit_one_off_profile() -> None:
    assert "migrate" not in _compose()["services"]
    migrate = _compose("--profile", "setup")["services"]["migrate"]
    assert migrate["profiles"] == ["setup"]
    assert migrate["command"] == ["python", "src/docker/boot.py", "migrate"]


def test_env_example_database_password_matches_its_url() -> None:
    values = dict(
        line.split("=", 1)
        for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#") and "=" in line
    )
    user, password = values["POSTGRES_USER"], values["POSTGRES_PASSWORD"]
    port, db = values["POSTGRES_PORT"], values["POSTGRES_DB"]
    assert values["DATABASE_URL"] == f"postgresql://{user}:{password}@127.0.0.1:{port}/{db}"
    assert "CAREERJET_LOCALE" in values
