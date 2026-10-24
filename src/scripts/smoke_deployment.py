"""Exercise the real root production launcher against an explicit local test database.

No migrations, seeds, model calls or account writes. Never targets a production database.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    database = os.environ.get("ADEPT_SMOKE_DATABASE_URL", "")
    if urlsplit(database).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("ADEPT_SMOKE_DATABASE_URL must name an explicit loopback test database.")
    port = os.environ.get("ADEPT_SMOKE_PORT", "13100")
    api_port = os.environ.get("ADEPT_SMOKE_API_PORT", "18200")
    origin = f"http://127.0.0.1:{port}"
    env = dict(
        os.environ,
        DATABASE_URL=database,
        APP_ENV="production",
        NODE_ENV="production",
        M3_BACKEND="postgres",
        PORT=port,
        API_PORT=api_port,
        WEB_ORIGIN=origin,
        CORS_ORIGINS=origin,
        SESSION_SECRET="synthetic-deployment-smoke-session-secret-32-plus",
        PROXY_SHARED_SECRET="synthetic-deployment-smoke-proxy-secret",
        TRUSTED_PROXY_HOPS="1",
        AUTH_MODE="demo",
        AUTH_DEFAULT_USER="",
        AUTH_RAW_USER_IDS="false",
        LLM_PROVIDER="none",
        EMBEDDINGS_PROVIDER="none",
    )

    def check(
        path: str,
        status: int = 200,
        method: str = "GET",
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[bytes, dict[str, str]]:
        req = urllib.request.Request(
            origin + path,
            data=body,
            method=method,
            headers={"X-Forwarded-For": "203.0.113.10", **(headers or {})},
        )
        try:
            response = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            if response.status != status:
                raise RuntimeError(f"{method} {path}: expected {status}, got {response.status}")
            print(f"{method} {path}: {response.status}", flush=True)
            return response.read(), dict(response.headers)

    with tempfile.TemporaryFile(mode="w+b") as log:
        options: dict[str, int] = (
            {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {}
        )
        process = subprocess.Popen(
            [sys.executable, "src/scripts/replit.py", "start"],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            **options,
        )
        failed = False
        try:
            deadline = time.monotonic() + 60
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Production launcher exited before readiness.")
                try:
                    with urllib.request.urlopen(origin + "/api/healthz", timeout=1) as ready:
                        if ready.status == 200:
                            break
                except (OSError, urllib.error.URLError):
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError("Public server did not become ready.")
                time.sleep(0.1)
            page, _ = check("/")
            for path in ["/about", "/auth/login", "/api/healthz", "/api/v1", "/api/v1/health"]:
                check(path)
            check("/api/healthz", method="HEAD")
            css = re.search(rb'/_next/static/[^"<> ]+\.css', page)
            if css is None:
                raise RuntimeError("Home page has no stylesheet reference.")
            check(css.group().decode())
            _, headers = check(
                "/api/v1/profile",
                method="OPTIONS",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization,x-workspace",
                },
            )
            if (
                next(
                    (v for k, v in headers.items() if k.lower() == "access-control-allow-origin"),
                    None,
                )
                != origin
            ):
                raise RuntimeError("CORS policy was lost at the public proxy.")
            check(
                "/api/v1/auth/login",
                status=401,
                method="POST",
                body=json.dumps(
                    {
                        "email": "nonexistent-smoke@example.test",
                        "password": "synthetic-not-a-password",
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            check("/api/v1/route-that-does-not-exist", status=404)
            print("Root deployment smoke passed; no account writes, migrations or model calls.")
            return 0
        except Exception:
            failed = True
            raise
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            check=False,
                            capture_output=True,
                        )
                    else:
                        process.kill()
                    process.wait()
            if failed:
                log.seek(0)
                print(log.read().decode(errors="replace"), file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
