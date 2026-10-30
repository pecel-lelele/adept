"""Real loopback HTTP journeys using the five labelled synthetic demo CVs.

The child API uses signed sessions, seed reference data and disposable memory stores.
It never opts into a developer database, provider, live feed or catalogue sync.
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "docs/demo-cvs/profiles.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def live_api() -> Iterator[httpx.Client]:
    """Run the unmodified API on an ephemeral loopback port, then stop only our child."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = os.environ.copy()
    environment.update(
        APP_ENV="development",
        M3_BACKEND="csv",
        DATABASE_URL="postgresql://adept:adept@127.0.0.1:1/adept_test_unreachable",
        AUTH_RAW_USER_IDS="false",
        AUTH_DEFAULT_USER="",
        SESSION_SECRET=secrets.token_urlsafe(48),
        PROXY_SHARED_SECRET="",
        LLM_PROVIDER="none",
        EMBEDDINGS_PROVIDER="none",
        LLM_API_KEY="",
        LLM_BASE_URL="",
        LLM_FALLBACK_PROVIDER="",
        LLM_FALLBACK_API_KEY="",
        RUNPOD_API_KEY="",
        GEMINI_API_KEY="",
        TRENDS_RUNPOD_API_KEY="",
        SYNC_TOKEN="",
        LOG_LEVEL="ERROR",
        PYTHONPATH=str(ROOT / "src/api"),
    )
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
            "--log-level",
            "error",
        ],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}/api/v1", timeout=20) as client:
            deadline = time.monotonic() + 20
            while True:
                if process.poll() is not None:
                    pytest.fail(f"Isolated API exited during startup: {process.returncode}")
                try:
                    if client.get("/profile/skills/catalogue").status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                if time.monotonic() >= deadline:
                    pytest.fail("Isolated API did not become ready within 20 seconds")
                time.sleep(0.1)
            yield client
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _json(response: httpx.Response, expected: int = 200) -> dict:
    # Do not expose token/password request or response bodies in assertion failures.
    error_code = response.json().get("error", {}).get("code") if response.is_error else None
    assert response.status_code == expected, (
        f"{response.request.method} {response.request.url.path}: "
        f"HTTP {response.status_code}, error_code={error_code}"
    )
    return response.json()


@pytest.mark.parametrize("case", CASES, ids=[case["user_id"] for case in CASES])
def test_synthetic_guest_pdf_preview(
    live_api: httpx.Client, case: dict, record_property: Callable[[str, object], None]
) -> None:
    """Guest availability must stand on its own, including a cold trend-cache request."""
    prefix = case["user_id"].removeprefix("demo-").replace("-", "_")
    pdf = next((ROOT / "docs/demo-cvs").glob(f"cv_{prefix}_*.pdf"))
    upload = {"file": (pdf.name, pdf.read_bytes(), "application/pdf")}
    response = live_api.post(
        "/preview/cv?include_suggestions=false",
        files=upload,
        data={"synthetic_consent": "true"},
    )
    if response.is_error:
        record_property("preview_error", json.dumps(response.json().get("error", {})))
    preview = _json(response)
    expected = {skill["skill_id"] for skill in case["skills"]}
    assert expected <= {skill["skill_id"] for skill in preview["skills"]}
    assert preview["top_role"] is not None
    assert preview["requires_skill_confirmation"] is True
    assert preview["truncated"] is False


@pytest.mark.parametrize("case", CASES, ids=[case["user_id"] for case in CASES])
def test_synthetic_pdf_to_saved_plan(
    live_api: httpx.Client, case: dict, record_property: Callable[[str, object], None]
) -> None:
    """Sign up, upload, confirm, rank, plan, save and reload over real HTTP."""
    prefix = case["user_id"].removeprefix("demo-").replace("-", "_")
    pdf = next((ROOT / "docs/demo-cvs").glob(f"cv_{prefix}_*.pdf"))
    upload = {"file": (pdf.name, pdf.read_bytes(), "application/pdf")}
    expected = {skill["skill_id"] for skill in case["skills"]}
    email = f"{case['user_id']}@example.test"
    password = secrets.token_urlsafe(24)
    session = _json(
        live_api.post(
            "/auth/signup",
            json={
                "display_name": f"Synthetic {case['display_name']}",
                "email": email,
                "password": password,
                "workspace": "individual",
                "consent": True,
            },
        ),
        201,
    )
    headers = {"X-Demo-User": session["token"]}
    assert _json(live_api.get("/auth/me", headers=headers))["id"] == session["account"]["id"]
    assert _json(live_api.get("/pathway/plans/me", headers=headers))["saved"] is None
    _json(
        live_api.post(
            "/profile/questionnaire",
            headers=headers,
            json={
                key: case[key]
                for key in (
                    "segment",
                    "interests",
                    "hours_per_week",
                    "learning_style",
                    "budget_myr",
                    "hrd_eligible",
                )
            },
        )
    )
    extraction = _json(
        live_api.post("/profile/cv?include_suggestions=false", files=upload, headers=headers)
    )
    assert expected <= {skill["skill_id"] for skill in extraction["skills"]}
    assert extraction["truncated"] is False
    assert _json(live_api.get("/profile/me", headers=headers))["skills"] == []
    # Explicit synthetic review follows demo-cvs/README.md; do not auto-approve all aliases.
    _json(live_api.put("/profile/skills/confirm", headers=headers, json={"skills": case["skills"]}))
    profile = _json(live_api.get("/profile/me", headers=headers))
    assert {skill["skill_id"] for skill in profile["skills"]} == expected

    rankings = {}
    for scenario in ("moderate", "fast"):
        matches = _json(live_api.get("/matches", headers=headers, params={"scenario": scenario}))
        assert matches["matches"]
        for match in matches["matches"]:
            assert match["meta"]["sources"]
            assert match["meta"]["scenario"] == scenario
            assert match["meta"]["is_estimate"] is True
        rankings[scenario] = matches["matches"][0]["role_id"]

    # The synthetic learner explicitly chooses the case's catalogue target role.
    role_id = case["current_role_id"]
    plan = _json(live_api.get("/pathway", headers=headers, params={"role_id": role_id}))
    assert plan["role_id"] == role_id
    assert plan["steps"]
    assert plan["meta"]["sources"]
    assert plan["hours_per_week"] == case["hours_per_week"]
    assert plan["within_budget"] is True
    catalogue = _json(live_api.get("/pathway/catalogue"))
    catalogue_ids = {course["id"] for course in catalogue["courses"]}
    assert all(
        course["id"] in catalogue_ids for step in plan["steps"] for course in step["courses"]
    )
    saved = _json(
        live_api.post(
            "/pathway/plans", headers=headers, json={"role_id": role_id, "scenario": "moderate"}
        )
    )
    assert saved["pathway"] == plan
    # Re-authenticate and reload through another signed session; no raw-user test bypass.
    login = _json(live_api.post("/auth/login", json={"email": email, "password": password}))
    reloaded = _json(live_api.get("/pathway/plans/me", headers={"X-Demo-User": login["token"]}))
    assert reloaded["saved"] == saved
    record_property(
        "synthetic_flow",
        json.dumps(
            {
                "case": case["user_id"],
                "extracted": len(extraction["skills"]),
                "confirmed": len(expected),
                "top_roles": rankings,
                "chosen_role": role_id,
                "steps": len(plan["steps"]),
                "weeks": plan["total_weeks"],
                "cost_myr": plan["out_of_pocket_myr"],
                "unmet": len(plan["unmet"]),
                "snapshot": plan["meta"]["snapshot_date"],
                "result": "saved_and_reloaded",
            }
        ),
    )


def test_public_preview_rejects_500_page_pdf(live_api: httpx.Client) -> None:
    with pymupdf.open() as document:
        for _ in range(500):
            document.new_page()
        content = document.tobytes()
    response = live_api.post(
        "/preview/cv?include_suggestions=false",
        files={"file": ("synthetic-500-pages.pdf", content, "application/pdf")},
        data={"synthetic_consent": "true"},
    )
    assert _json(response, 422)["error"]["code"] == "pdf_too_many_pages"
