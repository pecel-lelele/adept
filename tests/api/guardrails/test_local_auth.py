"""Authentication requires Adept's own signed, persisted account sessions."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.security import session


def test_unknown_auth_mode_fails_configuration() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_mode="external")  # type: ignore[arg-type]


def test_only_signed_local_account_sessions_authenticate(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_default_user", "")
    monkeypatch.setattr(settings, "auth_raw_user_ids", False)
    token = session.issue("aisyah")
    assert client.get("/api/v1/profile/me").status_code == 401
    assert (
        client.get("/api/v1/profile/me", headers={"Authorization": f"Bearer {token}"}).status_code
        == 401
    )
    assert client.get("/api/v1/profile/me", headers={"X-Demo-User": "aisyah"}).status_code == 401
    assert (
        client.get("/api/v1/profile/me", headers={"X-Demo-User": token + "invalid"}).status_code
        == 401
    )
    response = client.get("/api/v1/profile/me", headers={"X-Demo-User": token})
    assert response.status_code == 200
    assert response.json()["user_id"] == "aisyah"


def test_signed_session_requires_existing_account(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "auth_raw_user_ids", False)
    response = client.get(
        "/api/v1/profile/me", headers={"X-Demo-User": session.issue("synthetic-missing-account")}
    )
    assert response.status_code == 401
