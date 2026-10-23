#!/usr/bin/env python3
"""Run the existing Next.js and FastAPI apps in Replit without Docker or database setup."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import dev


def native_library_env() -> dict[str, str]:
    """Expose Replit's declared GCC runtime to binary Python wheels.

    Nix keeps libstdc++ outside the usual loader paths. Resolve it through the
    compiler rather than committing a machine-specific /nix/store path.
    """
    env = os.environ.copy()
    if not Path("/nix/store").is_dir():
        return env
    compiler = shutil.which("gcc")
    if compiler is None:
        raise dev.TaskError("GCC runtime is missing. Install the declared Replit gcc package.")
    result = subprocess.run(
        [compiler, "-print-file-name=libstdc++.so.6"],
        check=True,
        capture_output=True,
        text=True,
    )
    library = Path(result.stdout.strip())
    if not library.is_absolute() or not library.is_file():
        raise dev.TaskError("GCC could not locate libstdc++.so.6 required by PyMuPDF.")
    paths = [str(library.parent), env.get("LD_LIBRARY_PATH", "")]
    env["LD_LIBRARY_PATH"] = os.pathsep.join(path for path in paths if path)
    return env


def main() -> int:
    dev.load_env()
    # These are process-local preview settings, not changes to production configuration.
    origin = (
        f"https://{os.environ['REPLIT_DEV_DOMAIN']}"
        if os.environ.get("REPLIT_DEV_DOMAIN")
        else "http://localhost:5000"
    )
    os.environ.update(
        APP_ENV="development",
        NODE_ENV="development",
        API_PORT="8000",
        API_URL="http://127.0.0.1:8000",
        WEB_ORIGIN=origin,
        CORS_ORIGINS=origin,
    )
    next_cli = dev.WEB / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        print(
            "Next.js dependencies are missing. Run `pnpm --dir src/web install --frozen-lockfile`.",
            file=sys.stderr,
        )
        return 1
    python = dev.venv_python()
    if not python.exists():
        python = Path(sys.executable)

    # Replit stops the workflow with SIGTERM; let the existing supervisor clean up both servers.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    procs: dict[str, subprocess.Popen[bytes]] = {}
    try:
        api_env = native_library_env()
        procs["API"] = subprocess.Popen(
            [
                str(python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--reload",
            ],
            cwd=dev.API,
            env=api_env,
        )
        procs["web"] = subprocess.Popen(
            ["node", str(next_cli), "dev", "--hostname", "0.0.0.0", "--port", "5000"],
            cwd=dev.WEB,
            env=os.environ,
        )
        dev.log("Replit preview: Next.js on :5000; FastAPI on internal :8000 (no DB setup)")
        dev.supervise(procs)
    except (OSError, subprocess.CalledProcessError, dev.TaskError) as exc:
        print(f"Replit startup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        # Also cover a failure while launching the second process.
        for proc in procs.values():
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
