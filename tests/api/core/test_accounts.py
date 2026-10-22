"""Local accounts: sign-up, sign-in, signed sessions, organisation join codes."""

import uuid

from fastapi.testclient import TestClient

from app.core.security import session


def _email() -> str:
    return f"learner-{uuid.uuid4().hex[:8]}@example.test"


def _signup(client: TestClient, **extra: object) -> dict:
    body = {
        "display_name": "Test Learner",
        "email": _email(),
        "password": "correct horse battery",
        "consent": True,
        **extra,
    }
    resp = client.post("/api/v1/auth/signup", json=body)
    assert resp.status_code == 201, resp.text
    return {**resp.json(), "email": body["email"], "password": body["password"]}


def test_signup_then_login_returns_a_working_session(client: TestClient) -> None:
    created = _signup(client)
    assert created["next_path"] == "/app/onboarding"
    assert created["account"]["has_profile"] is False
    login = client.post(
        "/api/v1/auth/login", json={"email": created["email"], "password": created["password"]}
    )
    assert login.status_code == 200
    me = client.get("/api/v1/auth/me", headers={"X-Demo-User": login.json()["token"]})
    assert me.json()["id"] == created["account"]["id"]


def test_wrong_password_and_duplicate_email_are_rejected(client: TestClient) -> None:
    created = _signup(client)
    bad = client.post("/api/v1/auth/login", json={"email": created["email"], "password": "nope"})
    assert bad.status_code == 401
    assert bad.json()["error"]["message"] == "Email or password is incorrect."
    dup = client.post(
        "/api/v1/auth/signup",
        json={
            "display_name": "Other",
            "email": created["email"],
            "password": "another password",
            "consent": True,
        },
    )
    assert dup.status_code == 409


def test_tampered_or_expired_tokens_are_refused(client: TestClient) -> None:
    created = _signup(client)
    token = created["token"]
    forged = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    assert client.get("/api/v1/auth/me", headers={"X-Demo-User": forged}).status_code == 401
    expired = session.issue(created["account"]["id"], now=0)
    assert client.get("/api/v1/auth/me", headers={"X-Demo-User": expired}).status_code == 401


def test_new_learner_profile_is_saved_and_reloaded(client: TestClient) -> None:
    h = {"X-Demo-User": _signup(client)["token"]}
    client.post(
        "/api/v1/profile/questionnaire",
        json={
            "segment": "switcher",
            "interests": ["data"],
            "hours_per_week": 5,
            "budget_myr": 100,
            "hrd_eligible": False,
        },
        headers=h,
    )
    client.put(
        "/api/v1/profile/skills/confirm",
        json={"skills": [{"skill_id": "excel", "level": 3}]},
        headers=h,
    )
    me = client.get("/api/v1/profile/me", headers=h).json()
    assert me["segment"] == "switcher"
    assert [s["skill_id"] for s in me["skills"]] == ["excel"]
    assert client.get("/api/v1/auth/me", headers=h).json()["has_profile"] is True


def test_organisation_signup_and_member_join_by_code(client: TestClient) -> None:
    manager = _signup(
        client,
        workspace="organisation",
        organisation={"type": "company", "name": "Acme Ops", "industry": "Logistics", "size": 12},
    )
    assert manager["next_path"] == "/org"
    mh = {"X-Demo-User": manager["token"]}
    org = client.get("/api/v1/org/me", headers=mh).json()
    assert org["name"] == "Acme Ops" and org["join_code"]

    learner = _signup(client, join_code=org["join_code"])
    lh = {"X-Demo-User": learner["token"]}
    assert client.get("/api/v1/org/me", headers=lh).json()["join_code"] is None
    members = client.get("/api/v1/org/members", headers=mh).json()["members"]
    assert [m["id"] for m in members] == [learner["account"]["id"]]
    assert members[0]["intake_status"] == "in_progress"

    # A learner cannot edit the organisation.
    edit = {"type": "company", "name": "Hijack", "industry": "", "size": 1}
    assert client.put("/api/v1/org/me", json=edit, headers=lh).status_code == 403
    assert (
        client.delete(f"/api/v1/org/members/{learner['account']['id']}", headers=mh).status_code
        == 204
    )
    assert client.get("/api/v1/org/members", headers=mh).json()["members"] == []


def test_unknown_join_code_is_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/signup",
        json={
            "display_name": "X Y",
            "email": _email(),
            "password": "long enough pw",
            "consent": True,
            "join_code": "NOPE1234",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "bad_join_code"
