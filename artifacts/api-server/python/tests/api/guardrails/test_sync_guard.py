"""Sync endpoints rewrite reference data from external APIs: they must be locked down."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings

ENDPOINTS = ["/api/v1/pathway/catalogue/sync", "/api/v1/sdg/sync"]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_sync_is_disabled_without_a_configured_token(client: TestClient, path: str) -> None:
    resp = client.post(path, headers={"X-Sync-Token": "anything"})
    assert resp.status_code == 403


@pytest.mark.parametrize("path", ENDPOINTS)
def test_sync_rejects_a_wrong_or_missing_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setattr(get_settings(), "sync_token", "correct-token-value")
    assert client.post(path).status_code == 403
    assert client.post(path, headers={"X-Sync-Token": "wrong"}).status_code == 403


@pytest.mark.parametrize("path", ENDPOINTS)
def test_sync_needs_postgres(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setattr(get_settings(), "sync_token", "correct-token-value")
    resp = client.post(path, headers={"X-Sync-Token": "correct-token-value"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "sync_requires_postgres"
