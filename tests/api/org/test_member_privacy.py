"""Team members never see HR data: names, intake status, gaps, the group plan or team impact.

The /org pages already redirect members; these checks make sure the API refuses them too.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from harness.workspaces import BANK, work_headers

from app.features.org import repository

MEMBER = {"X-Demo-User": "aisyah"}  # a learner who belongs to the demo bank
MANAGER = {"X-Demo-User": "demo-company"}

TEAM_ONLY = [
    "/api/v1/org/members",
    "/api/v1/org/gaps",
    "/api/v1/org/plan",
    "/api/v1/sdg/contribution/org",
    "/api/v1/sdg/contribution/region/Kuala Lumpur",
]


@pytest.mark.parametrize("path", TEAM_ONLY)
def test_members_are_refused_team_data(client: TestClient, path: str) -> None:
    resp = client.get(path, headers=MEMBER)
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize("path", TEAM_ONLY)
def test_managers_still_see_their_team(client: TestClient, path: str) -> None:
    assert client.get(path, headers=MANAGER).status_code == 200


def test_region_impact_needs_a_signed_in_manager(client: TestClient) -> None:
    resp = client.get("/api/v1/sdg/contribution/region/Kuala Lumpur", headers={"X-Demo-User": "x"})
    assert resp.status_code in (401, 403)


def test_members_still_see_their_own_organisation_without_the_join_code(
    client: TestClient,
) -> None:
    resp = client.get("/api/v1/org/me", headers=MEMBER)
    assert resp.status_code == 200
    assert resp.json()["join_code"] is None


def test_current_role_is_hidden_without_sharing_consent(client: TestClient) -> None:
    def member() -> dict[str, object]:
        response = client.get("/api/v1/org/members", headers=MANAGER)
        assert response.status_code == 200
        return next(row for row in response.json()["members"] if row["id"] == "aisyah")

    before = member()["current_role_id"]
    assert before is not None
    try:
        assert (
            client.put(
                "/api/v1/org/me/sharing", headers=work_headers(), json={"share_skills": False}
            ).status_code
            == 200
        )
        assert member()["current_role_id"] is None
    finally:
        assert (
            client.put(
                "/api/v1/org/me/sharing", headers=work_headers(), json={"share_skills": True}
            ).status_code
            == 200
        )
    assert member()["current_role_id"] == before


def test_postgres_member_query_applies_current_role_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    calls: list[str] = []

    def execute(sql: str, params: tuple[str, ...]) -> SimpleNamespace:
        calls.append(sql)
        assert params == (BANK,)
        assert (
            "CASE WHEN m.share_skills THEN p.current_role_id ELSE NULL END AS current_role_id"
            in sql
        )
        return SimpleNamespace(fetchall=lambda: [])

    monkeypatch.setattr(repository, "use_postgres", lambda: True)
    monkeypatch.setattr(repository, "_db", lambda _, run: run(SimpleNamespace(execute=execute)))
    assert repository.list_members(BANK) == []
    assert len(calls) == 1
