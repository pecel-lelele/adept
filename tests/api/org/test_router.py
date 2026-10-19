from fastapi.testclient import TestClient

from app.contracts.org import GapHeatmapResponse, GroupPlan, MemberListResponse, Organization

COMPANY = {"X-Demo-User": "demo-company"}
INSTITUTION = {"X-Demo-User": "demo-institution"}


def test_my_org_company(client: TestClient) -> None:
    resp = client.get("/api/v1/org/me", headers=COMPANY)
    assert resp.status_code == 200
    assert Organization.model_validate(resp.json()).type == "company"


def test_my_org_institution(client: TestClient) -> None:
    resp = client.get("/api/v1/org/me", headers=INSTITUTION)
    assert Organization.model_validate(resp.json()).type == "institution"


def test_members(client: TestClient) -> None:
    resp = client.get("/api/v1/org/members", headers=COMPANY)
    assert resp.status_code == 200
    assert MemberListResponse.model_validate(resp.json()).members


def test_gaps(client: TestClient) -> None:
    resp = client.get("/api/v1/org/gaps", params={"scenario": "fast"}, headers=COMPANY)
    assert resp.status_code == 200
    body = GapHeatmapResponse.model_validate(resp.json())
    assert len(body.cells) == len(body.role_ids) * len(body.skills)
    assert body.meta.scenario == "fast"


def test_plan(client: TestClient) -> None:
    resp = client.get("/api/v1/org/plan", headers=COMPANY)
    assert resp.status_code == 200
    body = GroupPlan.model_validate(resp.json())
    assert body.steps and body.assigned_member_ids


def test_plan_follows_the_selected_scenario(client: TestClient) -> None:
    for scenario in ("moderate", "fast"):
        resp = client.get("/api/v1/org/plan", params={"scenario": scenario}, headers=COMPANY)
        assert resp.status_code == 200
        assert GroupPlan.model_validate(resp.json()).meta.scenario == scenario


def test_heatmap_is_computed_from_member_skills(client: TestClient) -> None:
    body = GapHeatmapResponse.model_validate(client.get("/api/v1/org/gaps", headers=COMPANY).json())
    cell = {(c.role_id, c.skill_id): c.gap for c in body.cells}
    # Two counted members (Aisyah, Employee 002); neither has RPA, so everyone is missing it.
    assert cell[("process-automation-analyst", "rpa")] == 1.0
    # A skill the role does not require is not a gap.
    assert cell[("process-automation-analyst", "sql")] == 0.0
    assert body.meta.sources[0].name != "MOCK DATA"


def test_group_plan_assigns_steps_to_members_who_need_them(client: TestClient) -> None:
    body = GroupPlan.model_validate(client.get("/api/v1/org/plan", headers=COMPANY).json())
    assert body.target_role_id == "process-automation-analyst"
    assert all(step.member_ids for step in body.steps)
    assert set(body.assigned_member_ids) <= {"aisyah", "emp-002"}


def test_group_plan_target_role_can_be_chosen(client: TestClient) -> None:
    resp = client.get("/api/v1/org/plan", params={"role_id": "data-analyst"}, headers=COMPANY)
    assert GroupPlan.model_validate(resp.json()).target_role_id == "data-analyst"
