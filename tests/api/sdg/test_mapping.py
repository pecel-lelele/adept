"""F6 mapping quality: every role and skill is mapped, to real targets, with real reasons."""

from fastapi.testclient import TestClient

from app.contracts.sdg import RegionListResponse, SdgAlignment, SdgContribution, SdgGoalListResponse
from app.core import seed
from app.features.sdg import repository


def test_all_17_goals_and_169_targets_are_served(client: TestClient) -> None:
    body = SdgGoalListResponse.model_validate(client.get("/api/v1/sdg/goals").json())
    assert [g.goal for g in body.goals] == list(range(1, 18))
    assert sum(len(g.targets) for g in body.goals) == 169
    assert body.focus_goals == [4, 5, 8, 9, 10]
    assert {g.goal for g in body.goals if g.is_focus} == {4, 5, 8, 9, 10}
    assert body.meta.sources[0].name == "UN Statistics Division SDG API"


def test_every_taxonomy_role_and_skill_has_at_least_one_link() -> None:
    roles = {r["id"] for r in seed.rows("taxonomy", "roles")}
    skills = {r["id"] for r in seed.rows("taxonomy", "skills")}
    assert roles - repository.mapped_role_ids() == set()
    assert skills - repository.mapped_skill_ids() == set()


def test_links_point_at_official_targets_with_meaningful_reasons() -> None:
    known = repository.targets()
    for table in ("role_sdg_map", "skill_sdg_map"):
        for row in seed.rows("sdg", table):
            assert row["sdg_target_id"] in known, row
            assert row["strength"] in {"direct", "enabling"}, row
            reason = row["reason"]
            assert len(reason) >= 30 and "mock" not in reason.lower(), row
            target = row["sdg_target_id"]
            assert target in reason or "indicator" in reason or "Adept" in reason, (
                f"reason should name the target it argues for: {row}"
            )


def test_draft_mappings_are_labelled_unreviewed(client: TestClient) -> None:
    body = client.get("/api/v1/sdg/roles/data-analyst").json()
    assert body["links"] and all(link["reviewed"] is False for link in body["links"])
    assert "pending review" in body["meta"]["sources"][1]["name"]


def test_person_contribution_follows_the_chosen_role(client: TestClient) -> None:
    def goals(role: str) -> set[str]:
        body = client.get("/api/v1/sdg/contribution/me", params={"role_id": role}).json()
        return {link["target"]["target"] for link in body["links"]}

    assert "16.4" in goals("compliance-analytics-officer")
    assert "16.4" not in goals("process-automation-analyst")


def test_person_contribution_includes_plan_level_links(client: TestClient) -> None:
    body = SdgContribution.model_validate(
        client.get("/api/v1/sdg/contribution/me", params={"role_id": "data-analyst"}).json()
    )
    via_plan = {link.target.target for link in body.links if link.via == "pathway"}
    assert via_plan == {"4.4", "4.3"}  # skills built; free / HRD-funded courses for Aisyah
    assert len(body.goals_summary) == 17 and body.meta.is_estimate
    assert sum(g.link_count for g in body.goals_summary) == len(body.links)


def test_org_contribution_counts_contributors(client: TestClient) -> None:
    resp = client.get("/api/v1/sdg/contribution/org", headers={"X-Demo-User": "demo-company"})
    body = SdgContribution.model_validate(resp.json())
    assert body.scope == "organisation" and body.scope_id == "org-demo-bank"
    goal8 = next(g for g in body.goals_summary if g.goal == 8)
    assert goal8.contributors >= 2  # Aisyah and Employee 002


def test_region_contribution(client: TestClient) -> None:
    regions = RegionListResponse.model_validate(client.get("/api/v1/sdg/regions").json())
    assert "Kuala Lumpur" in regions.regions
    body = client.get("/api/v1/sdg/contribution/region/Kuala Lumpur").json()
    assert SdgContribution.model_validate(body).scope == "region"
    assert client.get("/api/v1/sdg/contribution/region/Atlantis").status_code == 404


def test_alignment_ranks_roles_by_chosen_goals(client: TestClient) -> None:
    def score(role: str, goals: list[int]) -> float:
        resp = client.get(f"/api/v1/sdg/roles/{role}/alignment", params={"goals": goals})
        return SdgAlignment.model_validate(resp.json()).score

    assert score("compliance-analytics-officer", [16]) > score("data-analyst", [16]) == 0
    assert score("process-automation-analyst", [8]) > score("compliance-analytics-officer", [8])
    assert client.get("/api/v1/sdg/roles/x/alignment").status_code == 404
    assert client.get("/api/v1/sdg/roles/data-analyst/alignment?goals=18").status_code == 422
