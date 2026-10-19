from fastapi.testclient import TestClient

from app.contracts.trends import RadarResponse, RoleTrendResponse


def test_radar(client: TestClient) -> None:
    resp = client.get("/api/v1/trends/radar", params={"scenario": "fast"})
    assert resp.status_code == 200
    body = RadarResponse.model_validate(resp.json())
    assert body.items
    assert body.meta.scenario == "fast"
    assert body.meta.sources[0].name == "MOCK DATA"


def test_role_trend(client: TestClient) -> None:
    resp = client.get("/api/v1/trends/roles/data-analyst")
    assert resp.status_code == 200
    body = RoleTrendResponse.model_validate(resp.json())
    assert body.signal.entity_id == "data-analyst"


def test_role_trend_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/trends/roles/unknown-role").status_code == 404
