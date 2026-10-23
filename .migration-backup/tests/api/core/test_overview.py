"""Public platform overview: every figure comes from the app's own data (Core, M4)."""

from fastapi.testclient import TestClient

from app.core import overview
from app.features.pathway import data as pathway_data
from app.features.trends import service as trends_service


def test_overview_is_public_and_matches_the_data(client: TestClient) -> None:
    overview.reset()
    resp = client.get("/api/v1/meta/overview", headers={"X-Demo-User": ""})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    snap = trends_service.get_snapshot(None, "moderate")
    assert body["skills_tracked"] == len(snap.items)
    assert body["rising"] + body["stable"] + body["declining"] == len(snap.items)
    assert body["meta"]["snapshot_date"] == snap.meta.snapshot_date.isoformat()
    assert body["meta"]["is_estimate"] is True and body["meta"]["sources"]

    rising = [s["velocity"] for s in body["top_rising"]]
    assert rising == sorted(rising, reverse=True)
    assert all(s["direction"] == "rising" for s in body["top_rising"])
    assert all(s["direction"] == "declining" for s in body["top_declining"])

    courses = pathway_data.catalogue()
    assert body["courses"] == len(courses)
    assert body["free_courses"] == sum(1 for c in courses if c.cost_myr == 0)
    assert body["roles"] == len(pathway_data.target_role_ids())
    outlooks = [r["outlook"] for r in body["top_roles"]]
    assert outlooks == sorted(outlooks, reverse=True) and len(outlooks) <= 3
    assert 1 <= body["sdg_goals_linked"] <= 17
    assert body["skills_in_bank"] >= body["skills_tracked"] or body["skills_in_bank"] > 100
