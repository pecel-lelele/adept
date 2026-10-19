#!/usr/bin/env python3
"""Cross-platform task runner behind the Makefile.

Usage: python scripts/dev.py <task>   (or `make <task>`)

Kept stdlib-only so it runs before any virtualenv exists, and so Windows users
without `make` can call it directly.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "apps" / "api"
WEB = ROOT / "apps" / "web"
CONTRACT_FILES = ["apps/api/openapi.json", "apps/web/src/lib/api/types.ts"]


class TaskError(Exception):
    pass


def log(msg: str) -> None:
    print(f"\033[36m==>\033[0m {msg}", flush=True)


def load_env() -> None:
    """Load the root .env (or .env.example) into os.environ without overriding."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        env_file = ROOT / ".env.example"
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def pnpm() -> list[str]:
    found = shutil.which("pnpm")
    if found:
        return [found]
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    version = package["packageManager"].split("@", 1)[1]
    npx = shutil.which("npx")
    if not npx:
        raise TaskError("Neither pnpm nor npx found. Install Node.js 20+ first.")
    return [npx, "--yes", f"pnpm@{version}"]


def uv() -> list[str]:
    found = shutil.which("uv")
    if not found:
        raise TaskError("uv not found. Install it: https://docs.astral.sh/uv/")
    return [found]


def run(cmd: Sequence[str], cwd: Path = ROOT, check: bool = True) -> int:
    print(f"$ {' '.join(cmd)}", flush=True)
    code = subprocess.run(list(cmd), cwd=cwd, env=os.environ).returncode
    if check and code != 0:
        raise TaskError(f"command failed ({code}): {' '.join(cmd)}")
    return code


def api_run(*args: str, check: bool = True) -> int:
    return run([*uv(), "run", *args], cwd=API, check=check)


def web_run(*args: str, check: bool = True) -> int:
    return run([*pnpm(), "--filter", "web", *args], check=check)


# --- database ---------------------------------------------------------------


def docker_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    result = subprocess.run([docker, "info"], capture_output=True)
    return result.returncode == 0


def db_up(required: bool = True) -> bool:
    if not docker_available():
        msg = "Docker is not running; skipping the database (API serves mock data)."
        if required:
            raise TaskError(msg)
        log(msg)
        return False
    run(["docker", "compose", "up", "-d", "--wait", "db"])
    return True


def task_db_up() -> None:
    db_up(required=True)


def task_db_down() -> None:
    run(["docker", "compose", "down"])


def task_db_migrate() -> None:
    api_run("python", str(ROOT / "db" / "migrate.py"), "up")


def task_seed() -> None:
    api_run("python", str(ROOT / "db" / "seed.py"))


# --- lifecycle ----------------------------------------------------------------


def task_setup() -> None:
    if not (ROOT / ".env").exists():
        shutil.copy(ROOT / ".env.example", ROOT / ".env")
        log("Created .env from .env.example")
    log("Installing Python dependencies (uv)")
    run([*uv(), "sync"], cwd=API)
    log("Installing JS dependencies (pnpm)")
    run([*pnpm(), "install"])
    log("Starting database")
    if db_up(required=False):
        task_db_migrate()
        task_seed()
    log("Setup done. Next: make dev")


def task_dev() -> None:
    db_up(required=False)
    api_port = os.environ.get("API_PORT", "8000")
    log(f"API on http://localhost:{api_port}/docs  |  web on http://localhost:3000")
    procs = [
        subprocess.Popen(
            [*uv(), "run", "uvicorn", "app.main:app", "--reload", "--port", api_port],
            cwd=API,
            env=os.environ,
        ),
        subprocess.Popen([*pnpm(), "--filter", "web", "dev"], cwd=ROOT, env=os.environ),
    ]
    try:
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


# --- quality ------------------------------------------------------------------


def task_lint() -> None:
    api_run("ruff", "check", str(ROOT))
    api_run("ruff", "format", "--check", str(ROOT))
    web_run("lint")


def task_format() -> None:
    api_run("ruff", "check", "--fix", str(ROOT))
    api_run("ruff", "format", str(ROOT))


def task_test() -> None:
    api_run("pytest")


def task_typecheck() -> None:
    web_run("typecheck")


def task_contracts() -> None:
    """Regenerate openapi.json from the Pydantic contracts, then the TS types."""
    api_run("python", "-m", "app.export_openapi", str(API / "openapi.json"))
    web_run("contracts")


def task_contracts_check() -> None:
    task_contracts()
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *CONTRACT_FILES],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        print(result.stdout)
        raise TaskError(
            "Contract drift: generated files changed. Run `make contracts` and commit "
            "apps/api/openapi.json and apps/web/src/lib/api/types.ts."
        )
    log("Contracts in sync")


def task_check() -> None:
    steps: list[tuple[str, Callable[[], None]]] = [
        ("lint", task_lint),
        ("test", task_test),
        ("typecheck", task_typecheck),
        ("contracts", task_contracts_check),
    ]
    failed: list[str] = []
    for name, fn in steps:
        log(f"check: {name}")
        try:
            fn()
        except TaskError as exc:
            print(f"FAILED {name}: {exc}", file=sys.stderr)
            failed.append(name)
    if failed:
        raise TaskError(f"make check failed: {', '.join(failed)}")
    log("All checks passed")


TASKS: dict[str, Callable[[], None]] = {
    "setup": task_setup,
    "dev": task_dev,
    "check": task_check,
    "lint": task_lint,
    "format": task_format,
    "test": task_test,
    "typecheck": task_typecheck,
    "contracts": task_contracts,
    "contracts-check": task_contracts_check,
    "db-up": task_db_up,
    "db-down": task_db_down,
    "db-migrate": task_db_migrate,
    "seed": task_seed,
}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in TASKS:
        print(f"usage: python scripts/dev.py <{'|'.join(TASKS)}>", file=sys.stderr)
        return 2
    load_env()
    try:
        TASKS[argv[0]]()
    except TaskError as exc:
        print(f"\033[31merror:\033[0m {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
