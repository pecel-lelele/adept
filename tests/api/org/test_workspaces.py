"""Workspaces: one account, a personal workspace and one per organisation (M4-033)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from harness.workspaces import BANK, work_headers

HR = {"X-Demo-User": "demo-company", "X-Workspace": BANK}
PERSONAL = {"X-Demo-User": "aisyah", "X-Workspace": "personal"}
WORK = work_headers()


def _option_members(client: TestClient) -> set[str]:
    body = client.get("/api/v1/org/programmes/options", headers=HR).json()
    return {m["user_id"] for m in body["members"]}


def test_the_personal_workspace_cannot_reach_organisation_data(client: TestClient) -> None:
    assert client.get("/api/v1/org/me", headers=PERSONAL).status_code == 404
    assert client.get("/api/v1/org/programmes/mine", headers=PERSONAL).json() == {"assignments": []}
    assert client.get("/api/v1/org/me", headers=WORK).json()["name"] == "Demo Bank Berhad"


def test_a_workspace_needs_a_current_membership(client: TestClient) -> None:
    stranger = {"X-Demo-User": "aisyah", "X-Workspace": "org-demo-poly"}
    resp = client.get("/api/v1/org/me", headers=stranger)
    assert resp.status_code == 403 and resp.json()["error"]["code"] == "forbidden"


def test_management_rights_follow_the_membership_not_the_account(client: TestClient) -> None:
    assert client.get("/api/v1/org/members", headers=HR).status_code == 200
    manager_personal = {"X-Demo-User": "demo-company", "X-Workspace": "personal"}
    assert client.get("/api/v1/org/members", headers=manager_personal).status_code == 403
    assert client.get("/api/v1/org/members", headers=WORK).status_code == 403


def test_workspaces_list_personal_first_with_roles(client: TestClient) -> None:
    mine = client.get("/api/v1/org/workspaces", headers=PERSONAL).json()["workspaces"]
    assert mine[0] == {
        "id": "personal",
        "kind": "personal",
        "name": "",
        "org_type": None,
        "role": None,
        "skills_shared": False,
    }
    assert mine[1]["id"] == BANK and mine[1]["role"] == "member" and mine[1]["skills_shared"]
    hr = client.get("/api/v1/org/workspaces", headers=HR).json()["workspaces"]
    assert [w["role"] for w in hr] == [None, "manager"]


def test_managers_only_count_members_who_share_their_skills(client: TestClient) -> None:
    assert "aisyah" in _option_members(client)
    off = client.put("/api/v1/org/me/sharing", headers=WORK, json={"share_skills": False})
    assert off.status_code == 200 and off.json()["skills_shared"] is False
    assert "aisyah" not in _option_members(client)
    members = client.get("/api/v1/org/members", headers=HR).json()["members"]
    assert next(m for m in members if m["id"] == "aisyah")["skills_shared"] is False
    on = client.put("/api/v1/org/me/sharing", headers=WORK, json={"share_skills": True})
    assert on.json()["skills_shared"] is True
    assert "aisyah" in _option_members(client)


def test_sharing_is_changed_by_the_member_in_that_workspace(client: TestClient) -> None:
    body = {"share_skills": True}
    assert client.put("/api/v1/org/me/sharing", headers=PERSONAL, json=body).status_code == 403
    assert client.put("/api/v1/org/me/sharing", headers=HR, json=body).status_code == 403


def test_a_join_code_grants_membership_with_consent_and_shares_skills(
    client: TestClient,
) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "display_name": "Synthetic Joiner",
            "email": "synthetic.joiner@example.com",
            "password": "correct-horse-battery",
            "join_code": "BANKDEMO",
            "consent": True,
            "share_skills": True,
        },
    )
    assert signup.status_code == 201, signup.text
    token = signup.json()["token"]
    spaces = client.get("/api/v1/org/workspaces", headers={"X-Demo-User": token}).json()
    bank = next(w for w in spaces["workspaces"] if w["id"] == BANK)
    assert bank["role"] == "member" and bank["skills_shared"] is True
    joiner = signup.json()["account"]["id"]
    work = {"X-Demo-User": token, "X-Workspace": BANK}
    assert client.get("/api/v1/org/members", headers=work).status_code == 403
    # Synthetic Joiner has not completed profile intake yet, so not in option members
    assert joiner not in _option_members(client)


def test_joining_org_without_consent_fails(client: TestClient) -> None:
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "display_name": "No Consent Joiner",
            "email": "no.consent.joiner@example.com",
            "password": "correct-horse-battery",
            "consent": True,
        },
    )
    assert signup.status_code == 201
    token = signup.json()["token"]
    res = client.post(
        "/api/v1/org/join",
        headers={"X-Demo-User": token},
        json={"code": "BANKDEMO", "consent": False},
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "consent_required"
