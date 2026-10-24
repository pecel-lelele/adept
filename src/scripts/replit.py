#!/usr/bin/env python3
"""Build and supervise the production web/API pair on Replit Autoscale.

Stdlib only: the build command must work before dependencies are installed.
No Docker, model downloads, migrations or inference run during container startup.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "src" / "web"
STANDALONE = WEB / ".next" / "standalone" / "src" / "web"


class DeploymentError(Exception):
    """Actionable errors that never include credentials."""


def python_path() -> Path:
    return ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def configured_port() -> str:
    try:
        config = tomllib.loads((ROOT / ".replit").read_text(encoding="utf-8"))
        ports = [p["localPort"] for p in config.get("ports", []) if p.get("externalPort") == 80]
        if not ports:
            return "3000"
        if len(ports) != 1:
            raise DeploymentError("Configure exactly one external port 80 in .replit.")
        return str(ports[0])
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        raise DeploymentError("Cannot read port configuration from .replit.") from None


def native_library_env(source: Mapping[str, str]) -> dict[str, str]:
    """Resolve Nix's GCC runtime for PyMuPDF without hard-coding a store path."""
    env = dict(source)
    if Path("/nix/store").is_dir():
        compiler = shutil.which("gcc")
        if not compiler:
            raise DeploymentError("Add gcc to .replit [nix].packages for the PyMuPDF runtime.")
        result = subprocess.run(
            [compiler, "-print-file-name=libstdc++.so.6"],
            check=True,
            capture_output=True,
            text=True,
        )
        library = Path(result.stdout.strip())
        if not library.is_absolute() or not library.is_file():
            raise DeploymentError("GCC cannot locate the libstdc++ runtime required by PyMuPDF.")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            path for path in [str(library.parent), env.get("LD_LIBRARY_PATH", "")] if path
        )
    return env


def production_env(source: Mapping[str, str]) -> dict[str, str]:
    """Use platform secrets directly, never the development .env.example defaults."""
    env = dict(source)
    if not env.get("DATABASE_URL", "").strip():
        raise DeploymentError("DATABASE_URL is missing. Attach the Replit production database.")
    if len(env.get("SESSION_SECRET", "")) < 32:
        raise DeploymentError("SESSION_SECRET must contain at least 32 characters.")
    if not env.get("PROXY_SHARED_SECRET", "").strip():
        raise DeploymentError("PROXY_SHARED_SECRET is required on both web and API services.")
    hops = env.get("TRUSTED_PROXY_HOPS", "")
    if not hops.isascii() or not hops.isdecimal() or not 1 <= int(hops) <= 32:
        raise DeploymentError("TRUSTED_PROXY_HOPS must be a verified positive proxy count.")
    try:
        origin = urlsplit(env.get("WEB_ORIGIN", ""))
    except ValueError:
        raise DeploymentError("WEB_ORIGIN is not a valid origin.") from None
    if (
        origin.scheme not in {"http", "https"}
        or not origin.netloc
        or origin.username is not None
        or origin.path
        or origin.query
        or origin.fragment
    ):
        raise DeploymentError(
            "WEB_ORIGIN must be the app's exact origin, without a trailing slash."
        )
    try:
        port = int(env["PORT"] if "PORT" in env else configured_port())
        api_port = int(env.get("API_PORT", "8000"))
    except ValueError:
        raise DeploymentError("PORT must be an integer.") from None
    if not 1024 <= api_port <= 65535:
        raise DeploymentError("API_PORT must be 1024..65535.")
    if not 1024 <= port <= 65535 or port == api_port:
        raise DeploymentError("PORT must be 1024..65535 and different from API_PORT.")
    env.update(
        APP_ENV="production",
        NODE_ENV="production",
        M3_BACKEND="postgres",
        API_URL=f"http://127.0.0.1:{api_port}",
        API_PORT=str(api_port),
        PYTHONPATH=os.pathsep.join([str(ROOT / "src" / "api"), str(ROOT / "src")]),
        HOSTNAME="0.0.0.0",
        PORT=str(port),
        NEXT_TELEMETRY_DISABLED="1",
    )
    env.setdefault("CORS_ORIGINS", env["WEB_ORIGIN"])
    return env


def prepare_standalone() -> None:
    if not (STANDALONE / "server.js").is_file():
        raise DeploymentError("Next.js standalone server is missing. Run the build command first.")
    # Next's standalone output deliberately excludes these assets.
    for source, target in [
        (WEB / "public", STANDALONE / "public"),
        (WEB / ".next" / "static", STANDALONE / ".next" / "static"),
    ]:
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)


def build() -> None:
    print("[replit] Installing Python dependencies and building Next.js", flush=True)
    uv = shutil.which("uv")
    if uv:
        subprocess.run([uv, "sync", "--frozen"], cwd=ROOT, check=True)
    else:
        if not python_path().is_file():
            subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True)
        # uv-created development virtualenvs may not include pip.
        subprocess.run([str(python_path()), "-m", "ensurepip", "--upgrade"], check=True)
        install = [str(python_path()), "-m", "pip", "install"]
        subprocess.run([*install, "-r", str(ROOT / "requirements.txt")], cwd=ROOT, check=True)
    npx = shutil.which("npx")
    if not npx:
        raise DeploymentError("Node.js/npx is missing. Enable the nodejs-24 Replit module.")
    version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["packageManager"]
    pnpm = [npx, "--yes", version]
    env = dict(os.environ, NEXT_TELEMETRY_DISABLED="1", API_URL="http://127.0.0.1:8000")
    subprocess.run([*pnpm, "install", "--frozen-lockfile"], cwd=ROOT, env=env, check=True)
    subprocess.run([*pnpm, "build"], cwd=ROOT, env=env, check=True)
    prepare_standalone()
    print("[replit] Build complete. No database writes or model calls performed.", flush=True)


def doctor() -> dict[str, str]:
    """Print configuration status without secret values, DSNs or environment dumps."""
    issues: list[str] = []
    try:
        production_env(os.environ)
    except DeploymentError as exc:
        issues.append(str(exc))
    for path, label in [
        (python_path(), "Python virtualenv"),
        (STANDALONE / "server.js", "Web build"),
    ]:
        if not path.is_file():
            issues.append(f"{label} missing: run python3 src/scripts/replit.py build.")
    if not shutil.which("node"):
        issues.append("Node.js is missing: enable the nodejs-24 Replit module.")
    return {"status": "blocked" if issues else "ready", "details": " ".join(issues)}


def wait_for_api(
    process: subprocess.Popen[bytes], api_url: str = "http://127.0.0.1:8000", timeout: float = 45
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise DeploymentError("FastAPI exited during startup. Read the preceding API error.")
        try:
            with urllib.request.urlopen(api_url + "/api/v1/health", timeout=3) as response:
                health = json.load(response)
            if health.get("status") == "ok" and health.get("database") == "ok":
                return
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    raise DeploymentError("API/database did not become healthy within 45s. Check DATABASE_URL.")


def stop(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    for process in reversed(processes):
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def start() -> int:
    env = native_library_env(production_env(os.environ))
    diagnostics = doctor()
    if diagnostics["status"] != "ready":
        raise DeploymentError(diagnostics["details"])
    processes: list[subprocess.Popen[bytes]] = []

    def shutdown(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, shutdown)
    try:
        print(f"[replit] Starting private API on 127.0.0.1:{env['API_PORT']}", flush=True)
        processes.append(
            subprocess.Popen(
                [
                    str(python_path()),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    env["API_PORT"],
                ],
                cwd=ROOT,
                env=env,
            )
        )
        wait_for_api(processes[0], env["API_URL"])
        print(f"[replit] Starting public web on 0.0.0.0:{env['PORT']}", flush=True)
        processes.append(subprocess.Popen(["node", "server.js"], cwd=STANDALONE, env=env))
        while True:
            for name, process in zip(["API", "web"], processes, strict=True):
                code = process.poll()
                if code is not None:
                    print(f"[replit] {name} exited ({code}); stopping container.", flush=True)
                    return code or 1
            time.sleep(0.25)
    except KeyboardInterrupt:
        return 0
    finally:
        stop(processes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "start", "doctor"])
    args = parser.parse_args()
    try:
        if args.command == "build":
            build()
        elif args.command == "start":
            return start()
        else:
            result = doctor()
            print(json.dumps(result, indent=2))
            return int(result["status"] != "ready")
    except DeploymentError as exc:
        print(f"[replit] {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(
            f"[replit] Build step failed (exit {exc.returncode}); see output above.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
