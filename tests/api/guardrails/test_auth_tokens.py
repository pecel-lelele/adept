import time
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.auth import user_from_claims
from app.core.config import get_settings
from app.core.errors import AppError, UnauthorizedError
from app.core.security.tokens import bearer_token, decode_token

SECRET = "test-secret-not-real-0123456789abcdef"


def _token(**overrides: Any) -> str:
    claims: dict[str, Any] = {
        "sub": "user-123",
        "aud": "authenticated",
        "exp": int(time.time()) + 600,
        "app_metadata": {"kind": "org_admin", "org_id": "org-demo-bank"},
        "user_metadata": {"display_name": "Synthetic Tester"},
    }
    claims.update(overrides)
    return jwt.encode(claims, SECRET, algorithm="HS256")


def test_valid_token_decodes() -> None:
    assert decode_token(_token(), SECRET, "authenticated")["sub"] == "user-123"


@pytest.mark.parametrize(
    "token",
    [
        _token(exp=int(time.time()) - 10),
        _token(aud="anon"),
        jwt.encode({"sub": "x", "aud": "authenticated", "exp": 9e9}, "wrong", algorithm="HS256"),
        jwt.encode({"aud": "authenticated", "exp": 9e9}, SECRET, algorithm="HS256"),  # no sub
        "not-a-jwt",
    ],
)
def test_bad_tokens_are_unauthorized(token: str) -> None:
    with pytest.raises(UnauthorizedError):
        decode_token(token, SECRET, "authenticated")


def test_fails_closed_without_secret() -> None:
    with pytest.raises(AppError) as exc:
        decode_token(_token(), "", "authenticated")
    assert exc.value.status_code == 503


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer "])
def test_bearer_header_is_required(header: str | None) -> None:
    with pytest.raises(UnauthorizedError):
        bearer_token(header)


def test_privilege_comes_only_from_app_metadata() -> None:
    claims = jwt.decode(_token(), SECRET, algorithms=["HS256"], audience="authenticated")
    assert user_from_claims(claims).kind == "org_admin"
    claims["app_metadata"] = {}
    claims["user_metadata"] = {"kind": "org_admin"}  # user-editable: must be ignored
    assert user_from_claims(claims).kind == "learner"


def test_supabase_mode_end_to_end(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_mode", "supabase")
    monkeypatch.setattr(settings, "supabase_jwt_secret", SECRET)
    assert client.get("/api/v1/profile/me").status_code == 401
    ok = client.get("/api/v1/profile/me", headers={"Authorization": f"Bearer {_token()}"})
    assert ok.status_code == 200
    assert ok.json()["user_id"] == "user-123"
