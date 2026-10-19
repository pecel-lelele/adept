from fastapi.testclient import TestClient

from app.contracts.common import DataFreshness, HealthResponse
from app.main import discover_feature_routers

FEATURES = {"matching", "org", "pathway", "profile", "scenarios", "sdg", "trends"}


def test_health(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    HealthResponse.model_validate(resp.json())


def test_data_freshness(client: TestClient) -> None:
    resp = client.get("/api/v1/meta/data-freshness")
    assert resp.status_code == 200
    body = DataFreshness.model_validate(resp.json())
    assert body.sources[0].name == "MOCK DATA"


def test_all_feature_routers_discovered() -> None:
    assert {name for name, _ in discover_feature_routers()} == FEATURES


def test_unknown_demo_user_is_rejected(client: TestClient) -> None:
    resp = client.get("/api/v1/profile/me", headers={"X-Demo-User": "nobody"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"
