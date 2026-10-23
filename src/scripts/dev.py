#!/usr/bin/env python3
"""Cross-platform task runner behind the Makefile.

Usage: python src/scripts/dev.py <task>   (or `make <task>`)

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

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "src" / "api"
WEB = ROOT / "src" / "web"
DB = ROOT / "src" / "db"
VENV = ROOT / ".venv"
PYTHON_VERSION = "3.11"
CONTRACT_FILES = ["src/api/openapi.json", "src/web/src/lib/api/types.ts"]


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


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def py(*args: str) -> list[str]:
    python = venv_python()
    if not python.exists():
        raise TaskError("No .venv yet. Run `make setup` first.")
    return [str(python), *args]


def pnpm() -> list[str]:
    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    version = package["packageManager"].split("@", 1)[1]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", f"pnpm@{version}"]
    found = shutil.which("pnpm")
    if found:
        return [found]
    raise TaskError("Neither pnpm nor npx found. Install Node.js 20+ first.")


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


def web_run(*args: str) -> int:
    return run([*pnpm(), *args], cwd=WEB)


# --- database ---------------------------------------------------------------


def docker_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    return subprocess.run([docker, "info"], capture_output=True).returncode == 0


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
    run(py(str(DB / "migrate.py"), "up"))


def task_seed() -> None:
    run(py(str(DB / "seed.py")))


# --- lifecycle ----------------------------------------------------------------


def task_setup() -> None:
    if not (ROOT / ".env").exists():
        shutil.copy(ROOT / ".env.example", ROOT / ".env")
        log("Created .env from .env.example")
    log("Installing Python dependencies (uv + requirements.txt)")
    if not venv_python().exists():
        run([*uv(), "venv", "--python", PYTHON_VERSION, str(VENV)])
    run([*uv(), "pip", "install", "--python", str(venv_python()), "-r", "requirements.txt"])
    log("Installing JS dependencies (pnpm, src/web)")
    web_run("install")
    log("Starting database")
    if db_up(required=False):
        task_db_migrate()
        task_seed()
    log("Setup done. Next: make dev")


def task_dev() -> None:
    db_up(required=False)
    api_port = os.environ.get("API_PORT", "8000")
    log(f"API on http://localhost:{api_port}/docs  |  web on http://localhost:3000")
    procs = {
        "API": subprocess.Popen(
            py("-m", "uvicorn", "app.main:app", "--reload", "--port", api_port),
            cwd=API,
            env=os.environ,
        ),
        "web": subprocess.Popen([*pnpm(), "dev"], cwd=WEB, env=os.environ),
    }
    supervise(procs)


def supervise(procs: dict[str, subprocess.Popen[bytes]], poll_s: float = 0.5) -> None:
    """Wait until any child exits, stop the rest, and fail if a child died on its own.

    Ctrl+C is a normal stop. Any other exit (e.g. the web server cannot bind :3000)
    raises TaskError with the child's exit code, so `make dev` does not report success.
    """
    first: tuple[str, int] | None = None
    try:
        while first is None:
            for name, p in procs.items():
                code = p.poll()
                if code is not None:
                    first = (name, code)
                    break
            else:
                time.sleep(poll_s)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs.values():
            if p.poll() is None:
                p.terminate()
        for p in procs.values():
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    if first is not None:
        name, code = first
        raise TaskError(f"{name} server exited unexpectedly (exit code {code}).")


# --- quality ------------------------------------------------------------------


def task_lint() -> None:
    steps: list[tuple[str, Callable[[], int]]] = [
        ("ruff lint", lambda: run(py("-m", "ruff", "check", "."))),
        ("ruff format", lambda: run(py("-m", "ruff", "format", "--check", "."))),
        ("frontend lint", lambda: web_run("lint")),
    ]
    failed: list[str] = []
    for name, fn in steps:
        log(f"lint: {name}")
        try:
            fn()
        except TaskError as exc:
            print(f"FAILED {name}: {exc}", file=sys.stderr)
            failed.append(name)
        except Exception as exc:
            print(
                f"FAILED {name}: unexpected {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            failed.append(name)
    if failed:
        raise TaskError(f"make lint failed: {', '.join(failed)}")


def task_format() -> None:
    run(py("-m", "ruff", "check", "--fix", "."))
    run(py("-m", "ruff", "format", "."))


def task_test() -> None:
    run(py("-m", "pytest"))


def task_typecheck() -> None:
    web_run("typecheck")


def task_contracts() -> None:
    """Regenerate openapi.json from the Pydantic contracts, then the TS types."""
    run(py("-m", "app.export_openapi", str(API / "openapi.json")), cwd=API)
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
            + " and ".join(CONTRACT_FILES)
            + "."
        )
    log("Contracts in sync")


def _keys(node: object, prefix: str = "") -> set[str]:
    if not isinstance(node, dict):
        return {prefix}
    return {k for key, value in node.items() for k in _keys(value, f"{prefix}{key}.")}


def task_i18n_check() -> None:
    """Every locale must have the same namespaces and keys as English."""
    messages = WEB / "messages"
    base = {
        p.name: _keys(json.loads(p.read_text(encoding="utf-8"))) for p in messages.glob("en/*.json")
    }
    problems: list[str] = []
    for locale_dir in sorted(d for d in messages.iterdir() if d.is_dir() and d.name != "en"):
        for name, keys in base.items():
            path = locale_dir / name
            if not path.exists():
                problems.append(f"{locale_dir.name}/{name}: missing file")
                continue
            other = _keys(json.loads(path.read_text(encoding="utf-8")))
            for key in sorted(keys - other):
                problems.append(f"{locale_dir.name}/{name}: missing {key.rstrip('.')}")
            for key in sorted(other - keys):
                problems.append(f"{locale_dir.name}/{name}: extra {key.rstrip('.')}")
    if problems:
        print("\n".join(problems))
        raise TaskError("Translation keys differ from messages/en")
    log("Translations in sync")


def task_check() -> None:
    steps: list[tuple[str, Callable[[], None]]] = [
        ("lint", task_lint),
        ("i18n", task_i18n_check),
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
        except Exception as exc:
            print(
                f"FAILED {name}: unexpected {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
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
    "i18n-check": task_i18n_check,
    "db-up": task_db_up,
    "db-down": task_db_down,
    "db-migrate": task_db_migrate,
    "seed": task_seed,
}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in TASKS:
        print(f"usage: python src/scripts/dev.py <{'|'.join(TASKS)}>", file=sys.stderr)
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
