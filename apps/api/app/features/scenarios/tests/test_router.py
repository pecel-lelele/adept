from fastapi.testclient import TestClient

from app.contracts.scenarios import OutlookResponse, ScenarioListResponse


def test_list_scenarios(client: TestClient) -> None:
    resp = client.get("/api/v1/scenarios")
    assert resp.status_code == 200
    body = ScenarioListResponse.model_validate(resp.json())
    assert {s.id for s in body.scenarios} == {"moderate", "fast"}


def test_outlook_for_role(client: TestClient) -> None:
    resp = client.get("/api/v1/scenarios/outlook", params={"role_id": "data-analyst"})
    assert resp.status_code == 200
    body = OutlookResponse.model_validate(resp.json())
    assert {o.scenario for o in body.outlooks} == {"moderate", "fast"}
    assert all(o.low <= o.outlook <= o.high for o in body.outlooks)
    assert body.meta.is_estimate


def test_outlook_unknown_role(client: TestClient) -> None:
    assert client.get("/api/v1/scenarios/outlook", params={"role_id": "x"}).status_code == 404
