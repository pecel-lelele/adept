"""Synthetic regressions for live trust claims and cross-feature privacy boundaries."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from harness.workspaces import BANK, accept_work_plan, work_headers

from app.contracts.pathway import CompletionEvidence
from app.contracts.profile import Profile
from app.core.config import get_settings
from app.features.guardrails import service as guardrails
from app.features.impact import service as impact
from app.features.matching import repository as matching
from app.features.matching.scoring import MatchProfile, Role, Weights, _RoleScore
from app.features.org import service as org
from app.features.pathway import data, verification
from app.features.pathway import service as pathway
from app.features.profile import cv_parser
from app.features.profile import service as profile
from app.features.sdg import service as sdg
from app.main import app

HR = {"X-Demo-User": "demo-company"}
ROLE = "data-analyst"


def test_live_fairness_detects_a_biased_scorer(monkeypatch: pytest.MonkeyPatch) -> None:
    original = impact.rank_roles

    def biased(
        profile: MatchProfile,
        roles: list[Role],
        velocities: dict[str, float],
        weights: Weights,
        *,
        reference_velocities: dict[str, float] | None = None,
    ) -> list[_RoleScore]:
        ranked = original(
            profile, roles, velocities, weights, reference_velocities=reference_velocities
        )
        return list(reversed(ranked)) if "synthetic-identity-bias" in profile.interests else ranked

    original_adapter = matching.profile_to_match

    def identity_leak(profile: Profile, levels: dict[str, int]) -> MatchProfile:
        result = original_adapter(profile, levels)
        if profile.segment == "graduate":
            return MatchProfile(result.skills, result.interests | {"synthetic-identity-bias"})
        return result

    monkeypatch.setattr(matching, "profile_to_match", identity_leak)
    monkeypatch.setattr(impact, "rank_roles", biased)
    report = guardrails.get_fairness(app)
    assert not report.passed
    assert not report.counterfactual_checks[0].passed


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4])
def test_all_team_planning_paths_enforce_configured_cohort(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    learner = org.member_learners("org-demo-bank")["aisyah"]
    team = {f"synthetic-{i}": learner for i in range(count)}
    monkeypatch.setattr(org, "member_learners", lambda _org: team)
    monkeypatch.setattr(get_settings(), "org_min_cohort", 3)
    brief = {
        "title": "Synthetic cohort regression",
        "objectives": ["data_driven"],
        "roles": [{"role_id": ROLE, "headcount": max(1, count)}],
        "member_ids": list(team),
        "target_date": (datetime.now(UTC).date() + timedelta(weeks=12)).isoformat(),
        "hours_per_week": 4,
        "budget_total_myr": 0,
        "budget_per_member_myr": 0,
    }
    responses = [
        client.get("/api/v1/org/plan", headers=HR),
        client.get("/api/v1/org/packages", headers=HR),
        client.get("/api/v1/org/programmes/options", headers=HR),
        client.get("/api/v1/sdg/contribution/org", headers=HR),
    ]
    if count:
        responses.append(client.post("/api/v1/org/programmes/generate", headers=HR, json=brief))
    for response in responses:
        assert response.status_code == (409 if count < 3 else 200), response.text
        if count < 3:
            assert response.json()["error"]["code"] == "insufficient_cohort"
            assert "too few" in response.json()["error"]["message"].lower()


def test_selected_subset_cannot_bypass_cohort_gate(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    learner = org.member_learners("org-demo-bank")["aisyah"]
    team = {f"synthetic-{i}": learner for i in range(4)}
    monkeypatch.setattr(org, "member_learners", lambda _org: team)
    monkeypatch.setattr(get_settings(), "org_min_cohort", 4)
    assert client.get("/api/v1/org/packages", headers=HR).status_code == 200
    response = client.get("/api/v1/org/packages", headers=HR, params={"member_ids": list(team)[:2]})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_cohort"
    brief = {
        "title": "Synthetic selected subset",
        "objectives": ["data_driven"],
        "roles": [{"role_id": ROLE, "headcount": 2}],
        "member_ids": list(team)[:2],
        "target_date": (datetime.now(UTC).date() + timedelta(weeks=12)).isoformat(),
        "hours_per_week": 4,
        "budget_total_myr": 0,
        "budget_per_member_myr": 0,
    }
    response = client.post("/api/v1/org/programmes/generate", headers=HR, json=brief)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_cohort"


@pytest.mark.parametrize("link_status", ["provider_verified", "not_submitted"])
def test_submitted_link_never_earns_credit(link_status: str) -> None:
    course = next(c for c in data.catalogue() if c.skill_ids)
    evidence = CompletionEvidence(
        role_id=ROLE,
        course_id=course.id,
        kind="certificate_link",
        link_status=link_status,  # type: ignore[arg-type]
        submitted_at=datetime.now(UTC),
    )
    assert (
        pathway.earned_levels({course.id: course}, {course.id: "completed"}, {course.id: evidence})
        == {}
    )
    confirmed = evidence.model_copy(update={"kind": "org_confirmed"})
    assert pathway.earned_levels(
        {course.id: course}, {course.id: "completed"}, {course.id: confirmed}
    ) == dict.fromkeys(course.skill_ids, course.level)


@pytest.mark.parametrize(
    "url",
    ["https://www.credly.com/badges/another-person", "https://learn.microsoft.com/en-us/users/x/"],
)
def test_reachable_links_are_only_submitted(url: str) -> None:
    course = next(c for c in data.catalogue() if "Microsoft" in c.provider)
    assert verification.check_link(url, course, lambda _: 200) == "submitted"


@pytest.mark.parametrize(
    "prefix", ["seeking to learn", "want to learn", "hope to learn", "ingin belajar", "希望学习"]
)
def test_aspirations_do_not_extract_skills(prefix: str) -> None:
    assert not cv_parser.extract_skills(f"{prefix} Python, SQL and Excel.")
    assert {s.skill_id for s in cv_parser.extract_skills(f"{prefix} SQL.\nSkills: Python")} == {
        "python"
    }


def test_get_pathway_requires_saved_profile(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(profile, "has_profile", lambda _: False)
    response = client.get("/api/v1/pathway", params={"role_id": ROLE})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "profile_required"


@pytest.mark.parametrize("sharing", [True, False])
def test_actual_sharing_members_define_planning_cohort(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, sharing: bool
) -> None:
    members = org.repository._members["org-demo-bank"]
    monkeypatch.setitem(
        org.repository._members,
        "org-demo-bank",
        [
            m.model_copy(update={"skills_shared": sharing}) if m.id == "aisyah" else m
            for m in members
        ],
    )
    assert len(org.member_learners("org-demo-bank")) == (2 if sharing else 1)
    for endpoint in ("org/plan", "org/packages", "org/programmes/options", "sdg/contribution/org"):
        response = client.get(f"/api/v1/{endpoint}", headers=HR)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "insufficient_cohort"


def test_leadership_actions_resolve_only_when_catalogued(monkeypatch: pytest.MonkeyPatch) -> None:
    text = "Lead a team. Managed people."
    assert not cv_parser.extract_skills(text)  # current catalogue has no leadership record
    taxonomy = dict(cv_parser._load_taxonomy())
    taxonomy["synthetic-leadership"] = cv_parser.TaxonomySkill(
        "synthetic-leadership", "Leadership", "leadership", ()
    )
    monkeypatch.setattr(cv_parser, "_load_taxonomy", lambda: taxonomy)
    cv_parser._build_alias_index.cache_clear()
    try:
        for phrase in ("Lead a team", "Managed people"):
            found = cv_parser.extract_skills(phrase)
            assert [s.skill_id for s in found] == ["synthetic-leadership"]
            assert found[0].label == "Leadership"
        assert not cv_parser.extract_skills("Hope to lead a team")
    finally:
        cv_parser._build_alias_index.cache_clear()


def test_zero_learning_price_never_implies_hrd_funding_or_free_certificate() -> None:
    from app.core.auth import CurrentUser

    plan = pathway.get_pathway(CurrentUser("aisyah", "Synthetic", "learner"), ROLE, "moderate")
    free = plan.model_copy(update={"out_of_pocket_myr": 0, "hrd_eligible": True})
    link = next(link for link in sdg.plan_links(free) if link.target.target == "4.3")
    assert link.reason == "Every course in this plan is free to learn (certificate fees may apply)."
    assert "HRD" not in link.reason


def test_submitted_credential_changes_neither_matching_nor_team_gaps_until_review(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.features.pathway import repository

    repository.reset()
    role = "process-automation-analyst"
    plan = accept_work_plan(role)
    course = next(
        c
        for step in plan.steps
        for c in step.courses
        if c.level >= step.target_level and "Microsoft" in c.provider
    )
    before_match = matching.load_profile("aisyah").skills
    before_team = org.member_learners(BANK)
    before_gaps = pathway.team_gaps(before_team, [role])
    monkeypatch.setattr(verification, "probe", lambda _: 200)
    response = client.post(
        "/api/v1/pathway/progress/evidence",
        headers=work_headers(),
        json={
            "role_id": role,
            "course_id": course.id,
            "url": "https://learn.microsoft.com/en-us/users/another-person/transcript/",
        },
    )
    assert response.status_code == 200, response.text
    evidence = response.json()["evidence"][course.id]
    assert evidence["kind"] == "certificate_link" and evidence["link_status"] == "submitted"
    assert matching.load_profile("aisyah").skills == before_match
    assert org.member_learners(BANK) == before_team
    assert pathway.team_gaps(org.member_learners(BANK), [role]) == before_gaps
    confirmed = client.post(
        "/api/v1/pathway/verifications",
        headers=HR,
        json={
            "user_id": "aisyah",
            "role_id": role,
            "course_id": course.id,
            "decision": "confirm",
            "submitted_at": evidence["submitted_at"],
        },
    )
    assert confirmed.status_code == 200, confirmed.text
    assert matching.load_profile("aisyah").skills != before_match
    assert pathway.team_gaps(org.member_learners(BANK), [role]) != before_gaps
    repository.reset()
