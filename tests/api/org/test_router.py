import pytest
from fastapi.testclient import TestClient

from app.contracts.org import (
    GapHeatmapResponse,
    GroupPlan,
    Member,
    MemberListResponse,
    Organization,
)
from app.features.org import repository
from app.features.profile import repository as profile_repository


@pytest.fixture
def three_member_cohort(monkeypatch: pytest.MonkeyPatch) -> None:
    """A third synthetic consenting learner tests values above the real default threshold."""
    member = Member(
        id="synthetic-cohort-third",
        display_name="Synthetic third member",
        current_role_id=None,
        intake_status="complete",
        skills_shared=True,
    )
    monkeypatch.setitem(
        repository._members, "org-demo-bank", [*repository._members["org-demo-bank"], member]
    )
    monkeypatch.setitem(
        profile_repository._store,
        member.id,
        profile_repository._store["emp-002"].model_copy(update={"user_id": member.id}),
    )


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


def test_heatmap_is_computed_from_member_skills(
    client: TestClient, three_member_cohort: None
) -> None:
    body = GapHeatmapResponse.model_validate(client.get("/api/v1/org/gaps", headers=COMPANY).json())
    cell = {(c.role_id, c.skill_id): c.gap for c in body.cells}
    # Three consenting completed members; none has RPA, so everyone is missing it.
    assert cell[("process-automation-analyst", "rpa")] == 1.0
    # A skill the role does not require is not a gap.
    assert cell[("process-automation-analyst", "sql")] == 0.0
    assert body.meta.sources[0].name != "MOCK DATA"


def test_group_plan_assigns_steps_to_members_who_need_them(client: TestClient) -> None:
    body = GroupPlan.model_validate(client.get("/api/v1/org/plan", headers=COMPANY).json())
    assert body.target_role_id == "customer-success-specialist"
    assert all(step.member_ids for step in body.steps)
    assert set(body.assigned_member_ids) <= {"aisyah", "emp-002"}


def test_group_plan_target_role_can_be_chosen(client: TestClient) -> None:
    resp = client.get("/api/v1/org/plan", params={"role_id": "data-analyst"}, headers=COMPANY)
    assert GroupPlan.model_validate(resp.json()).target_role_id == "data-analyst"


def test_role_gaps_average_required_skills_and_pick_the_default_target(
    client: TestClient,
    three_member_cohort: None,
) -> None:
    """Zero cells for skills a role does not require must not dilute its average."""
    body = GapHeatmapResponse.model_validate(client.get("/api/v1/org/gaps", headers=COMPANY).json())
    assert set(body.role_gaps) == set(body.role_ids)
    for role in body.role_ids:
        all_cells = [c.gap for c in body.cells if c.role_id == role]
        assert all(c is not None for c in all_cells)
        naive = sum(c for c in all_cells if c is not None) / len(all_cells)
        assert body.role_gaps[role] is not None
        assert body.role_gaps[role] >= naive - 1e-6
    plan = GroupPlan.model_validate(client.get("/api/v1/org/plan", headers=COMPANY).json())
    # The bank cohort already has customer-service skills, and no UX skills.
    assert plan.target_role_id == "customer-success-specialist"
    assert plan.target_role_id != "ux-designer"


def test_heatmap_date_uses_the_same_scopes_as_the_learners(client: TestClient, monkeypatch) -> None:
    from app.features.pathway import service as pathway_service
    from app.features.profile import repository as profile_repository

    learner_scopes: list[list[str]] = []
    date_scopes: list[list[str]] = []
    real = pathway_service.evidenced_levels_many

    def spy_levels(user_ids, scopes):  # noqa: ANN001
        learner_scopes.append(list(scopes))
        return real(user_ids, scopes)

    def spy_date(user_ids, scopes):  # noqa: ANN001,ARG001
        date_scopes.append(list(scopes))

    monkeypatch.setattr(pathway_service, "evidenced_levels_many", spy_levels)
    monkeypatch.setattr(profile_repository, "observed_on", spy_date)
    assert (
        client.get("/api/v1/org/gaps", params={"scenario": "fast"}, headers=COMPANY).status_code
        == 200
    )
    assert date_scopes and date_scopes[-1] == learner_scopes[0]


def test_personal_scope_needs_every_included_member_to_share() -> None:
    from app.features.org import service as org_service

    base = {"name": "Synthetic", "role": "member", "intake_status": "complete"}
    shared = Member.model_construct(id="a", skills_shared=True, **base)
    private = Member.model_construct(id="b", skills_shared=False, **base)
    assert "personal" in org_service._progress_scopes("o1", [shared])
    assert org_service._progress_scopes("o1", [shared, private]) == ["org:o1"]
