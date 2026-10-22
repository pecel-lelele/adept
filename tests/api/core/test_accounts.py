"""Local accounts: sign-up, sign-in, signed sessions, organisation join codes."""

import uuid

import pytest
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


def _org(client: TestClient, name: str) -> tuple[dict, str]:
    manager = _signup(
        client,
        workspace="organisation",
        organisation={"type": "company", "name": name, "industry": "Finance", "size": 5},
    )
    headers = {"X-Demo-User": manager["token"]}
    return headers, client.get("/api/v1/org/me", headers=headers).json()["join_code"]


def test_member_cannot_join_a_second_organisation(client: TestClient) -> None:
    first_h, first_code = _org(client, "First Co")
    _, second_code = _org(client, "Second Co")
    learner = _signup(client, join_code=first_code)
    lh = {"X-Demo-User": learner["token"]}
    again = client.post("/api/v1/org/join", json={"code": first_code}, headers=lh)
    assert again.status_code == 200  # rejoining the same organisation is harmless
    other = client.post("/api/v1/org/join", json={"code": second_code}, headers=lh)
    assert other.status_code == 409
    assert other.json()["error"]["code"] == "already_member"
    assert client.get("/api/v1/org/me", headers=lh).json()["name"] == "First Co"

    # Once removed, the member is free to join another organisation.
    member_id = learner["account"]["id"]
    assert client.delete(f"/api/v1/org/members/{member_id}", headers=first_h).status_code == 204
    moved = client.post("/api/v1/org/join", json={"code": second_code}, headers=lh)
    assert moved.status_code == 200
    assert moved.json()["name"] == "Second Co"


def test_failed_organisation_setup_undoes_the_signup(client: TestClient, monkeypatch) -> None:
    from app.core.refdata import StorageUnavailableError
    from app.features.accounts import service

    def boom(*_: object) -> None:
        raise StorageUnavailableError("could not create the organisation")

    monkeypatch.setattr(service.org_service, "create_org", boom)
    body = {
        "display_name": "Stranded Manager",
        "email": _email(),
        "password": "correct horse battery",
        "consent": True,
        "workspace": "organisation",
        "organisation": {"type": "company", "name": "Gone", "industry": "", "size": 3},
    }
    assert client.post("/api/v1/auth/signup", json=body).status_code == 503
    monkeypatch.undo()
    # The email is free again, so the same person can simply retry.
    assert client.post("/api/v1/auth/signup", json=body).status_code == 201


def test_export_and_delete_my_account(client: TestClient) -> None:
    """PDPA: a person can download their data and delete their account with their password."""
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "display_name": "Delete Me",
            "email": "delete.me@example.test",
            "password": "correct-horse-1",
            "consent": True,
        },
    )
    assert signup.status_code == 201, signup.text
    token = signup.json()["token"]
    headers = {"X-Demo-User": token}

    exported = client.get("/api/v1/auth/me/export", headers=headers)
    assert exported.status_code == 200
    assert exported.json()["account"]["email"] == "delete.me@example.test"
    assert "attachment" in exported.headers["content-disposition"]

    wrong = client.post("/api/v1/auth/me/delete", json={"password": "nope"}, headers=headers)
    assert wrong.status_code == 401

    gone = client.post(
        "/api/v1/auth/me/delete", json={"password": "correct-horse-1"}, headers=headers
    )
    assert gone.status_code == 204
    again = client.post(
        "/api/v1/auth/login",
        json={"email": "delete.me@example.test", "password": "correct-horse-1"},
    )
    assert again.status_code == 401


def test_login_does_the_same_work_for_unknown_emails(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unknown email still runs a password check, so timing does not reveal accounts."""
    from app.core.security import session
    from app.features.accounts import service

    calls: list[str | None] = []
    real = session.check_password

    def spy(password: str, stored: str | None) -> bool:
        calls.append(stored)
        return real(password, stored)

    monkeypatch.setattr(session, "check_password", spy)
    from app.core.errors import UnauthorizedError

    with pytest.raises(UnauthorizedError):
        service.login(service.LoginIn(email="nobody@example.test", password="whatever-1"))
    assert calls and calls[0] and calls[0].startswith("scrypt$")


def test_export_includes_learning_records(client: TestClient) -> None:
    """The download holds plans, course progress and badges, not just the account."""
    headers = {"X-Demo-User": "aisyah"}
    plan = client.post(
        "/api/v1/pathway/plans",
        json={"role_id": "data-analyst", "scenario": "moderate"},
        headers=headers,
    )
    assert plan.status_code == 200, plan.text
    course_id = plan.json()["pathway"]["steps"][0]["courses"][0]["id"]
    done = client.post(
        "/api/v1/pathway/progress",
        json={"role_id": "data-analyst", "course_id": course_id, "status": "completed"},
        headers=headers,
    )
    assert done.status_code == 200, done.text
    body = client.get("/api/v1/auth/me/export", headers=headers).json()
    assert body["saved_plan"]["role_id"] == "data-analyst"
    assert any(r["course_id"] == course_id and r["status"] == "completed" for r in body["learning"])
    assert body["badges"], "the first completed course earns a badge"
