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


AUTHORITATIVE = (
    "https://sdgs.un.org/goals/",  # official UN target definitions
    "https://unstats.un.org/sdgs/metadata/",
    "https://www.ilo.org/",
    "https://www.unesco.org/",
    "https://gcedclearinghouse.org/",  # UNESCO Clearinghouse on GCED (APCEIU)
)


def test_every_link_cites_an_authoritative_source() -> None:
    for table in ("role_sdg_map", "skill_sdg_map"):
        for row in seed.rows("sdg", table):
            assert row["evidence_url"].startswith(AUTHORITATIVE), row
            assert row["evidence_source"] and len(row["evidence_note"]) >= 40, row


def test_new_role_evidence_contains_the_actual_official_target_text() -> None:
    labels = {r["id"]: r["label"] for r in seed.rows("sdg", "sdg_targets")}
    for row in seed.rows("sdg", "role_sdg_map"):
        if (
            row["evidence_source"]
            == "United Nations Sustainable Development Goals: official target definition"
        ):
            assert labels[row["sdg_target_id"]] in row["evidence_note"]
            assert ": ." not in row["evidence_note"]


def test_links_and_plan_links_carry_evidence(client: TestClient) -> None:
    body = SdgContribution.model_validate(
        client.get("/api/v1/sdg/contribution/me", params={"role_id": "data-analyst"}).json()
    )
    assert body.links and all(link.evidence and link.evidence.source.url for link in body.links)


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
    hr = {"X-Demo-User": "demo-company"}
    body = client.get("/api/v1/sdg/contribution/region/Kuala Lumpur", headers=hr).json()
    assert SdgContribution.model_validate(body).scope == "region"
    assert client.get("/api/v1/sdg/contribution/region/Atlantis", headers=hr).status_code == 404


def test_alignment_ranks_roles_by_chosen_goals(client: TestClient) -> None:
    def score(role: str, goals: list[int]) -> float:
        resp = client.get(f"/api/v1/sdg/roles/{role}/alignment", params={"goals": goals})
        return SdgAlignment.model_validate(resp.json()).score

    assert score("compliance-analytics-officer", [16]) > score("data-analyst", [16]) == 0
    assert score("process-automation-analyst", [8]) > score("compliance-analytics-officer", [8])
    assert client.get("/api/v1/sdg/roles/x/alignment").status_code == 404
    assert client.get("/api/v1/sdg/roles/data-analyst/alignment?goals=18").status_code == 422


def test_org_and_region_contribution_follow_the_selected_role(
    client: TestClient, monkeypatch
) -> None:
    """H05: the role chosen on the team plan drives the organisation's impact view."""
    company = {"X-Demo-User": "demo-company"}
    default = client.get("/api/v1/sdg/contribution/org", headers=company).json()
    roles = client.get("/api/v1/pathway/targets", headers=company)
    role_ids = (
        [r["role_id"] for r in roles.json().get("roles", [])] if roles.status_code == 200 else []
    )
    other = next((r for r in role_ids if r not in default["role_ids"]), "data-analyst")
    chosen = client.get(
        "/api/v1/sdg/contribution/org", params={"role_id": other}, headers=company
    ).json()
    assert chosen["role_ids"] == [other]
    assert chosen["role_ids"] != default["role_ids"]
    from app.features.sdg import service

    seen = []
    build = service.org_service.member_plans

    def record(org_id, scenario, role_id=None):
        seen.append(role_id)
        return build(org_id, scenario, role_id)

    monkeypatch.setattr(service.org_service, "member_plans", record)
    region = client.get(
        "/api/v1/sdg/contribution/region/Kuala Lumpur", params={"role_id": other}, headers=company
    ).json()
    assert seen and all(role == other for role in seen)
    assert region["aggregation_status"] == "suppressed"
    assert region["role_ids"] == []
    unknown = client.get(
        "/api/v1/sdg/contribution/org", params={"role_id": "astronaut"}, headers=company
    )
    assert unknown.status_code == 404
