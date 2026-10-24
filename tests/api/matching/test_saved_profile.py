"""Tests for Prompt 3: matching uses the saved profile, not cached CSVs.

Rules tested:
1. Save profile with Python level 1 -> match score for role needing Python.
   Update profile to Python level 5 -> score must change (increase).
2. A user with no saved profile gets a clear 4xx error ("profile required"),
   not an empty match list.
3. personas.py is not imported by any production matching module.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.features.profile import repository as profile_repo

USER_HEADER = {"X-Demo-User": "weijie"}


@pytest.fixture(autouse=True)
def _isolate_profile_store():
    """Preserve and restore in-memory profile store so tests leave no side effects."""
    snapshot = {k: v.model_copy(deep=True) for k, v in profile_repo._store.items()}
    yield
    profile_repo._store.clear()
    profile_repo._store.update(snapshot)


def test_score_updates_when_saved_profile_changes(client: TestClient) -> None:
    """Save profile with Python level 1, verify score.

    Update profile to Python level 5, verify score for data-analyst changes.
    """
    # 1. Save profile with Python level 1
    resp = client.put(
        "/api/v1/profile/skills/confirm",
        json={"skills": [{"skill_id": "python", "level": 1}]},
        headers=USER_HEADER,
    )
    assert resp.status_code == 200

    resp1 = client.get("/api/v1/matches", params={"scenario": "moderate"}, headers=USER_HEADER)
    assert resp1.status_code == 200, f"Expected 200, got {resp1.status_code}: {resp1.text}"
    body1 = resp1.json()
    matches1 = {m["role_id"]: m["score"] for m in body1["matches"]}
    assert "data-analyst" in matches1
    score_lvl1 = matches1["data-analyst"]

    # 2. Update profile to Python level 5
    resp = client.put(
        "/api/v1/profile/skills/confirm",
        json={"skills": [{"skill_id": "python", "level": 5}]},
        headers=USER_HEADER,
    )
    assert resp.status_code == 200

    resp2 = client.get("/api/v1/matches", params={"scenario": "moderate"}, headers=USER_HEADER)
    assert resp2.status_code == 200, f"Expected 200, got {resp2.status_code}: {resp2.text}"
    body2 = resp2.json()
    matches2 = {m["role_id"]: m["score"] for m in body2["matches"]}
    assert "data-analyst" in matches2
    score_lvl5 = matches2["data-analyst"]

    # Score must have changed (increased) because Python is required for data-analyst
    assert score_lvl5 > score_lvl1, (
        f"Score did not increase after upgrading Python level from 1 to 5: "
        f"lvl1={score_lvl1}, lvl5={score_lvl5}"
    )


def test_user_with_no_saved_profile_gets_clear_error(client: TestClient) -> None:
    """A user who has not completed/saved a profile must get a 4xx profile-required error."""
    # "demo-institution" is in DEMO_USERS but has no profile in the profile store
    headers = {"X-Demo-User": "demo-institution"}
    resp = client.get("/api/v1/matches", params={"scenario": "moderate"}, headers=headers)

    assert 400 <= resp.status_code < 500, (
        f"Expected 4xx error for missing profile, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "error" in body, f"Expected error payload, got: {body}"
    err = body["error"]
    assert err.get("code") == "profile_required" or "profile" in err.get("message", "").lower(), (
        f"Expected clear profile required error, got: {err}"
    )

    # Individual role match endpoint must also return 4xx
    resp_role = client.get(
        "/api/v1/matches/data-analyst", params={"scenario": "moderate"}, headers=headers
    )
    assert 400 <= resp_role.status_code < 500


def test_personas_not_imported_by_production_matching_modules() -> None:
    """Production matching code must not import personas.py."""
    matching_dir = (
        Path(__file__).resolve().parents[3] / "src" / "api" / "app" / "features" / "matching"
    )
    assert matching_dir.is_dir()

    production_files = [
        f for f in matching_dir.glob("*.py") if f.name not in ("personas.py", "__init__.py")
    ]
    assert len(production_files) >= 5, f"Expected production files, found: {production_files}"

    import_re = re.compile(
        r"^\s*(?:from\s+[\.\w]*personas\b|import\s+[\.\w]*personas\b)",
        re.MULTILINE,
    )

    for py_file in production_files:
        content = py_file.read_text(encoding="utf-8")
        match = import_re.search(content)
        assert match is None, (
            f"Production module '{py_file.name}' imports personas: {match.group(0)}"
        )
