from fastapi.testclient import TestClient

from app.contracts.sdg import EntitySdgLinks, SdgContribution


def test_role_sdg(client: TestClient) -> None:
    resp = client.get("/api/v1/sdg/roles/data-analyst")
    assert resp.status_code == 200
    body = EntitySdgLinks.model_validate(resp.json())
    assert body.links and all(link.reason for link in body.links)


def test_skill_sdg(client: TestClient) -> None:
    resp = client.get("/api/v1/sdg/skills/python")
    assert resp.status_code == 200
    assert EntitySdgLinks.model_validate(resp.json()).entity_type == "skill"


def test_contribution(client: TestClient) -> None:
    resp = client.get("/api/v1/sdg/contribution/me")
    assert resp.status_code == 200
    body = SdgContribution.model_validate(resp.json())
    assert sum(g.link_count for g in body.goals_summary) == len(body.links)


def test_unknown_role(client: TestClient) -> None:
    assert client.get("/api/v1/sdg/roles/unknown").status_code == 404
