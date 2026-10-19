from fastapi.testclient import TestClient

from app.contracts.matching import MatchResponse, RoleMatch


def test_list_matches_sorted_with_meta(client: TestClient) -> None:
    resp = client.get("/api/v1/matches", params={"scenario": "moderate"})
    assert resp.status_code == 200
    body = MatchResponse.model_validate(resp.json())
    scores = [m.score for m in body.matches]
    assert scores == sorted(scores, reverse=True)
    assert all(m.meta.is_estimate for m in body.matches)


def test_scenario_changes_scores(client: TestClient) -> None:
    moderate = client.get("/api/v1/matches", params={"scenario": "moderate"}).json()
    fast = client.get("/api/v1/matches", params={"scenario": "fast"}).json()
    assert [m["score"] for m in moderate["matches"]] != [m["score"] for m in fast["matches"]]


def test_get_match(client: TestClient) -> None:
    resp = client.get("/api/v1/matches/data-analyst", params={"scenario": "fast"})
    assert resp.status_code == 200
    body = RoleMatch.model_validate(resp.json())
    assert abs(body.score - sum(c.weight * c.value for c in body.components)) < 1e-6


def test_get_match_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/matches/unknown").status_code == 404
