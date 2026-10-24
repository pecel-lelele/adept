"""Team members never see HR data: names, intake status, gaps, the group plan or team impact.

The /org pages already redirect members; these checks make sure the API refuses them too.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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
