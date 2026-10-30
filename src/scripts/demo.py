"""Loopback demo preparation. Credentials come from environment variables, never arguments.

warmup reads stored data only. account creates a labelled synthetic learner; --reset is
allowed only against a development API on loopback and the reserved example.test domain.
"""

from __future__ import annotations

import argparse
import os
from urllib.parse import urlsplit

import httpx


def require_local_development(base: str, environment: str) -> None:
    target = urlsplit(base)
    if (
        target.scheme != "http"
        or target.username is not None
        or target.hostname not in {"127.0.0.1", "localhost", "::1"}
    ):
        raise ValueError("Demo account operations require a loopback HTTP development API")
    if environment != "development":
        raise ValueError("Refusing to change demo accounts on a production API")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["warmup", "account"])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default="synthetic.demo@example.test")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=15, follow_redirects=False) as client:
        if args.action == "warmup":
            for path in ["/api/v1/health", "/api/v1/meta/version", "/api/v1/trends/snapshot"]:
                response = client.get(path)
                response.raise_for_status()
                print(f"{path}: {response.status_code}")
            return 0
        # Check the target before sending account credentials or changing anything.
        require_local_development(args.base_url, "development")
        info = client.get("/api/v1/meta/version")
        info.raise_for_status()
        require_local_development(args.base_url, info.json()["environment"])
        if not args.email.startswith("synthetic.") or not args.email.endswith("@example.test"):
            raise ValueError("Use a synthetic.*@example.test account")
        password = os.environ.get("ADEPT_DEMO_PASSWORD", "")
        if len(password) < 12:
            raise ValueError("Set ADEPT_DEMO_PASSWORD to a test-only password of 12+ characters")
        if args.reset:
            login = client.post(
                "/api/v1/auth/login", json={"email": args.email, "password": password}
            )
            if login.status_code != 401:
                login.raise_for_status()
                deleted = client.post(
                    "/api/v1/auth/me/delete",
                    headers={"X-Demo-User": login.json()["token"]},
                    json={"password": password},
                )
                deleted.raise_for_status()
        created = client.post(
            "/api/v1/auth/signup",
            json={
                "email": args.email,
                "password": password,
                "display_name": "Synthetic Demo Learner",
                "consent": True,
            },
        )
        created.raise_for_status()
        print("Synthetic learner ready. Sign in through the local web app; no token is printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
