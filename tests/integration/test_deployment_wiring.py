"""Production proxy and scheduler regressions for the relocated workspace."""

import subprocess
from pathlib import Path

import pytest
import yaml

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = ROOT


@pytest.mark.parametrize("secret", ["", "   "])
def test_missing_proxy_secret_blocks_production(secret: str) -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        session_secret="synthetic-session-secret-with-32-characters",
        auth_raw_user_ids=False,
        auth_default_user="",
        proxy_shared_secret=secret,
        trusted_proxy_hops=1,
    )
    errors, _ = settings.deployment_problems()
    assert any("PROXY_SHARED_SECRET" in error for error in errors)


def test_trusted_proxy_mode_requires_a_positive_hop_count_in_production() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        session_secret="synthetic-session-secret-with-32-characters",
        auth_raw_user_ids=False,
        auth_default_user="",
        proxy_shared_secret="synthetic-proxy-secret",
        trusted_proxy_hops=0,
        proxy_client_ip_mode="trusted",
        m3_backend="postgres",
        web_origin="https://adept.example.test",
    )
    assert any("TRUSTED_PROXY_HOPS" in error for error in settings.deployment_problems()[0])
    settings.trusted_proxy_hops = 1
    assert not settings.deployment_problems()[0]


def test_secret_files_are_ignored_at_every_application_depth() -> None:
    paths = [
        ".env",
        ".env.production",
        ".session-secret",
        "src/web/.env.local",
        "src/api/.session-secret",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "--stdin", "-z"],
        cwd=ROOT,
        input=("\0".join(paths) + "\0").encode(),
        capture_output=True,
        check=True,
    )
    assert set(result.stdout.decode().strip("\0").split("\0")) == set(paths)
    example = subprocess.run(
        ["git", "check-ignore", "--no-index", ".env.example"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert example.returncode == 1


def test_refresh_schedules_run_from_the_repository_root() -> None:
    for name in ["trends-refresh.yml", "data-sources.yml"]:
        with (ROOT / ".github/workflows" / name).open() as stream:
            workflow = yaml.safe_load(stream)
        trigger = workflow.get("on", workflow.get(True))
        assert trigger["schedule"]
        for job in workflow["jobs"].values():
            directory = ROOT / job["defaults"]["run"]["working-directory"]
            assert directory == PYTHON_ROOT
            assert (directory / "requirements.txt").is_file()
            assert (directory / "src/pipelines/trends/preflight.py").is_file()
    assert (ROOT / ".github/workflows/ci.yml").is_file()
    assert (ROOT / ".github/workflows/publish-minilm.yml").is_file()
