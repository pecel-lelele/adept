"""GitHub is only a clock: call/poll the deployed app without DB or model credentials."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def request(path: str, *, method: str = "GET") -> dict:
    base = os.environ.get("DATA_REFRESH_APP_URL", "").rstrip("/")
    token = os.environ.get("DATA_REFRESH_TOKEN", "")
    parts = urlsplit(base)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.path not in ("", "/")
        or not token
    ):
        raise RuntimeError("Configure DATA_REFRESH_APP_URL and DATA_REFRESH_TOKEN")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args: object, **kwargs: object) -> None:
            return None

    opener = urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(
        base + path,
        method=method,
        headers={"X-Data-Refresh-Token": token, "Accept": "application/json"},
    )
    for attempt in range(4):
        try:
            with opener.open(req, timeout=45) as response:
                result = json.loads(response.read(1_000_001))
            if not isinstance(result, dict):
                raise ValueError("Invalid refresh response")
            return result
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 502, 503, 504) or attempt == 3:
                raise RuntimeError(f"Refresh HTTP failure ({exc.code})") from None
        except (OSError, ValueError):
            if attempt == 3:
                raise RuntimeError("Refresh endpoint did not respond") from None
        time.sleep((10, 20, 30)[attempt])
    raise RuntimeError("Refresh unavailable")


def main() -> int:
    result = request("/api/v1/data/refresh/run", method="POST")
    if result.get("status") == "up_to_date":
        print("Refresh cadence already satisfied; no model work requested.")
        return 0
    if result.get("status") == "cooldown":
        print("Refresh is still due but cooling down; automatic refresh was not completed.")
        return 1
    run_id = result.get("run_id")
    from uuid import UUID

    run_id = str(UUID(str(run_id)))
    deadline = time.monotonic() + 960
    while result.get("status") in ("queued", "running") and time.monotonic() < deadline:
        time.sleep(5)
        result = request(f"/api/v1/data/refresh/status/{run_id}")
    for step in result.get("steps", []):
        print(f"{step['source']}: {step['status']} ({step.get('rows', 0)} rows)")
    if result.get("status") != "ok":
        print("Refresh failed or timed out; the app retains each source's last good data.")
        return 1
    print("Automatic refresh completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
