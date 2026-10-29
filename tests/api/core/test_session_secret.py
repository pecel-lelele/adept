"""The fallback session key is random, never derived from public settings (Core, M4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import REPO_ROOT, Settings, get_settings
from app.core.security import session


@pytest.fixture
def no_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(get_settings(), "session_secret", "")
    monkeypatch.setattr(session, "_fallback", None)
    path = tmp_path / ".session-secret"
    monkeypatch.setattr(session, "SECRET_FILE", path)
    return path


def test_fallback_key_is_random_and_kept(no_secret: Path) -> None:
    key = session._secret()
    assert len(key) == 32
    assert no_secret.read_text(encoding="ascii") == key.hex()
    token = session.issue("someone")
    assert session.verify(token) == "someone"


def test_fallback_key_is_not_derived_from_database_url(no_secret: Path) -> None:
    import hashlib

    derived = hashlib.sha256(("adept-dev-session:" + get_settings().database_url).encode()).digest()
    assert session._secret() != derived


def test_stored_key_survives_a_restart(no_secret: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = session._secret()
    monkeypatch.setattr(session, "_fallback", None)
    assert session._secret() == first


def test_configured_secret_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "session_secret", "configured")
    assert session._secret() == b"configured"


def test_concurrent_first_use_creates_one_key(no_secret: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=16) as pool:
        keys = list(pool.map(lambda _: session._secret(), range(64)))
    assert len(set(keys)) == 1
    assert no_secret.read_text(encoding="ascii") == keys[0].hex()


def test_existing_key_file_from_another_process_is_reused(
    no_secret: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = "ab" * 32
    no_secret.write_text(other, encoding="ascii")
    assert session._secret() == bytes.fromhex(other)


def test_example_does_not_publish_a_session_key() -> None:
    lines = (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    assert [line for line in lines if line.startswith("SESSION_SECRET=")] == ["SESSION_SECRET="]


@pytest.mark.parametrize("app_env", ["development", "production"])
def test_public_example_key_is_rejected(app_env: str) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="public example key is unsafe"):
        Settings(
            _env_file=None,
            app_env=app_env,
            session_secret="change-me-to-a-long-random-string-of-32-plus-chars",
        )


def test_token_signed_with_public_example_key_is_rejected(no_secret: Path) -> None:
    import base64
    import hashlib
    import hmac

    payload = "v1.c3ludGhldGljLWFjY291bnQ.2000000000"
    signature = hmac.new(
        b"change-me-to-a-long-random-string-of-32-plus-chars",
        payload.encode(),
        hashlib.sha256,
    ).digest()
    token = payload + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")
    assert session.verify(token, now=1000000000) is None
