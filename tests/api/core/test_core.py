from fastapi.testclient import TestClient

from app.contracts.common import DataFreshness, HealthResponse
from app.main import discover_feature_routers

FEATURES = {
    "accounts",
    "assistant",
    "guardrails",
    "matching",
    "org",
    "pathway",
    "preview",
    "profile",
    "scenarios",
    "sdg",
    "trends",
}


def test_health(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    HealthResponse.model_validate(resp.json())


def test_data_freshness(client: TestClient) -> None:
    resp = client.get("/api/v1/meta/data-freshness")
    assert resp.status_code == 200
    body = DataFreshness.model_validate(resp.json())
    # Real snapshot sources, never the old placeholder.
    assert body.is_mock is False
    assert body.sources and all(s.name != "MOCK DATA" and s.url for s in body.sources)


def test_all_feature_routers_discovered() -> None:
    assert {name for name, _ in discover_feature_routers()} == FEATURES


def test_unknown_demo_user_is_rejected(client: TestClient) -> None:
    resp = client.get("/api/v1/profile/me", headers={"X-Demo-User": "nobody"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"
