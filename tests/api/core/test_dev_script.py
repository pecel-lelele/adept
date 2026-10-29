"""`make dev` must fail when one of its servers dies (review finding P2)."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

DEV_PY = Path(__file__).resolve().parents[3] / "src" / "scripts" / "dev.py"


def _load_dev() -> ModuleType:
    spec = importlib.util.spec_from_file_location("adept_dev_script", DEV_PY)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _child(code: str) -> subprocess.Popen[bytes]:
    return subprocess.Popen([sys.executable, "-c", code])


def test_supervise_raises_with_the_failed_childs_exit_code() -> None:
    dev = _load_dev()
    procs = {
        "API": _child("import time; time.sleep(30)"),
        "web": _child("import sys; sys.exit(3)"),
    }
    with pytest.raises(dev.TaskError, match=r"web server exited unexpectedly \(exit code 3\)"):
        dev.supervise(procs, poll_s=0.05)
    assert procs["API"].poll() is not None, "the surviving server must be stopped"


def test_supervise_treats_a_clean_exit_as_unexpected_too() -> None:
    dev = _load_dev()
    procs = {"API": _child("pass"), "web": _child("import time; time.sleep(30)")}
    with pytest.raises(dev.TaskError, match="API server exited unexpectedly"):
        dev.supervise(procs, poll_s=0.05)


@pytest.mark.parametrize("task", ["task_db_up", "task_db_down"])
def test_database_tasks_select_only_the_database_compose_file(
    monkeypatch: pytest.MonkeyPatch, task: str
) -> None:
    dev = _load_dev()
    commands: list[list[str]] = []
    monkeypatch.setattr(dev, "docker_available", lambda: True)
    monkeypatch.setattr(dev, "run", lambda cmd: commands.append(cmd))
    getattr(dev, task)()
    expected = ["up", "-d", "--wait", "db"] if task == "task_db_up" else ["down"]
    assert commands == [["docker", "compose", "-f", "docker-compose.db.yml", *expected]]


def _compose_config(compose_file: str, secret: str | None) -> subprocess.CompletedProcess[str]:
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Docker Compose CLI is not installed; no daemon is needed")
    root = DEV_PY.parents[2]
    env = {k: v for k, v in os.environ.items() if not k.startswith("COMPOSE_")}
    env.pop("SESSION_SECRET", None)
    if secret is not None:
        env["SESSION_SECRET"] = secret
    env.update(
        POSTGRES_USER="adept",
        POSTGRES_PASSWORD="synthetic-config-check-only",
        POSTGRES_DB="adept",
        POSTGRES_BIND="127.0.0.1",
        POSTGRES_PORT="5433",
    )
    return subprocess.run(
        [
            docker,
            "compose",
            "--env-file",
            str(root / ".env.example"),
            "-f",
            str(root / compose_file),
            "config",
            "--format",
            "json",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize("secret", [None, ""])
def test_database_compose_resolves_without_an_api_secret(secret: str | None) -> None:
    result = _compose_config("docker-compose.db.yml", secret)
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    assert set(config["services"]) == {"db"}
    assert "SESSION_SECRET" not in config["services"]["db"]["environment"]
    assert config["services"]["db"]["ports"][0]["host_ip"] == "127.0.0.1"


@pytest.mark.parametrize("secret", [None, ""])
def test_full_stack_still_requires_an_api_secret(secret: str | None) -> None:
    result = _compose_config("docker-compose.yml", secret)
    assert result.returncode != 0
    assert "SESSION_SECRET is required" in result.stderr


def test_full_stack_reuses_the_same_database_and_volume() -> None:
    db = _compose_config("docker-compose.db.yml", None)
    stack = _compose_config("docker-compose.yml", "synthetic-compose-test-secret-32-characters")
    assert db.returncode == 0, db.stderr
    assert stack.returncode == 0, stack.stderr
    db_config, stack_config = json.loads(db.stdout), json.loads(stack.stdout)
    assert set(stack_config["services"]) == {"db", "api", "web"}
    assert db_config["services"]["db"] == stack_config["services"]["db"]
    assert db_config["volumes"] == stack_config["volumes"]
