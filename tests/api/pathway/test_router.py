from fastapi.testclient import TestClient

from app.contracts.pathway import Pathway


def test_pathway(client: TestClient) -> None:
    resp = client.get("/api/v1/pathway", params={"role_id": "data-analyst", "scenario": "fast"})
    assert resp.status_code == 200
    body = Pathway.model_validate(resp.json())
    assert [s.order for s in body.steps] == list(range(1, len(body.steps) + 1))
    assert body.total_weeks == body.steps[-1].week_end
    assert body.meta.scenario == "fast"


def test_pathway_requires_role(client: TestClient) -> None:
    assert client.get("/api/v1/pathway").status_code == 422


def test_pathway_unknown_role(client: TestClient) -> None:
    assert client.get("/api/v1/pathway", params={"role_id": "x"}).status_code == 404
