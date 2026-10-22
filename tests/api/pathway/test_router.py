from fastapi.testclient import TestClient

from app.contracts.matching import MatchResponse
from app.contracts.pathway import CatalogueResponse, Pathway
from app.features.pathway import data

AISYAH = {"X-Demo-User": "aisyah"}
WEIJIE = {"X-Demo-User": "weijie"}


def _pathway(
    client: TestClient, role: str, headers: dict[str, str] = AISYAH, scenario: str = "moderate"
) -> Pathway:
    resp = client.get(
        "/api/v1/pathway", params={"role_id": role, "scenario": scenario}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    return Pathway.model_validate(resp.json())


def test_pathway(client: TestClient) -> None:
    resp = client.get("/api/v1/pathway", params={"role_id": "data-analyst", "scenario": "fast"})
    assert resp.status_code == 200
    body = Pathway.model_validate(resp.json())
    assert [s.order for s in body.steps] == list(range(1, len(body.steps) + 1))
    assert body.total_weeks == body.steps[-1].week_end
    assert body.meta.scenario == "fast"


def test_pathway_without_role_uses_the_saved_plan_or_asks_to_choose(client: TestClient) -> None:
    resp = client.get("/api/v1/pathway", headers={"X-Demo-User": "ravi"})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "role_required"


def test_pathway_unknown_role(client: TestClient) -> None:
    assert client.get("/api/v1/pathway", params={"role_id": "x"}).status_code == 404


def test_every_suggested_match_has_a_pathway(client: TestClient) -> None:
    """Review finding P1: 'Plan a pathway' must work for every match shown."""
    for scenario in ("moderate", "fast"):
        matches = MatchResponse.model_validate(
            client.get("/api/v1/matches", params={"scenario": scenario}).json()
        )
        for m in matches.matches:
            assert _pathway(client, m.role_id, scenario=scenario).steps, m.role_id


def test_recommends_only_catalogue_courses(client: TestClient) -> None:
    catalogue = {c.id: c for c in data.catalogue()}
    for role in data.role_labels():
        if not data.requirements(role):
            continue
        for step in _pathway(client, role).steps:
            for c in [*step.courses, *step.alternatives]:
                assert catalogue[c.id] == c, f"{c.id} is not the catalogue record"


def test_every_course_carries_url_source_and_verified_date(client: TestClient) -> None:
    body = CatalogueResponse.model_validate(client.get("/api/v1/pathway/catalogue").json())
    assert body.courses
    for c in body.courses:
        assert c.url.startswith("https://") and c.source and c.source.retrieved_at
        assert c.verified_at <= c.source.retrieved_at or c.verified_at == c.source.retrieved_at
    assert not body.meta.is_estimate


def test_schedule_uses_profile_hours_per_week(client: TestClient) -> None:
    aisyah = _pathway(client, "data-analyst")
    assert aisyah.hours_per_week == 6
    assert aisyah.total_weeks == -(-aisyah.total_hours // 6)


def test_budget_and_hrd_fields_are_explained(client: TestClient) -> None:
    body = _pathway(client, "data-analyst")
    assert body.hrd_eligible and body.budget_myr == 500
    assert body.within_budget and body.out_of_pocket_myr <= body.budget_myr
    hrd = [a for s in body.steps for a in s.alternatives if a.hrd_claimable]
    assert hrd and all(a.hrd_note for a in hrd)


def test_steps_link_to_sdg_targets(client: TestClient) -> None:
    body = _pathway(client, "process-automation-analyst")
    assert all(step.sdg_targets for step in body.steps)


def test_prerequisite_order_for_aisyah(client: TestClient) -> None:
    order = [s.skill_id for s in _pathway(client, "process-automation-analyst").steps]
    assert order.index("process-mapping") < order.index("rpa")


def test_unmet_skill_is_reported_not_invented(client: TestClient) -> None:
    # Catalogue risk & compliance courses stop at level 2; the role needs 3.
    body = _pathway(client, "compliance-analytics-officer", headers={"X-Demo-User": "ravi"})
    unmet = {u.skill_id: u for u in body.unmet}
    assert unmet["risk-compliance"].reason == "catalogue_tops_out"


def test_unknown_paid_certificate_price_does_not_promise_full_skill_coverage(
    client: TestClient,
) -> None:
    body = _pathway(client, "ai-operations-specialist", headers=WEIJIE)
    assert "prompt-engineering" in {u.skill_id for u in body.unmet}
    assert all(c.price_status == "listed" for s in body.steps for c in s.courses)


def test_subscriptions_are_never_booked_as_steps(client: TestClient) -> None:
    for role in data.role_labels():
        if not data.requirements(role):
            continue
        for step in _pathway(client, role).steps:
            assert all(c.format != "subscription" for c in step.courses), role


def test_catalogue_filters(client: TestClient) -> None:
    def ids(**params: object) -> list[str]:
        body = CatalogueResponse.model_validate(
            client.get("/api/v1/pathway/catalogue", params=params).json()
        )
        return [c.id for c in body.courses]

    hrd = ids(hrd_claimable=True)
    assert hrd and "ukm-data-analytics-certificate" in hrd and "mslearn-tsql" not in hrd
    assert ids(format="subscription") == ["coursera-plus-annual"]
    assert set(ids(skill="excel")) >= {
        "unimas-excel-booster",
        "coursera-excel-basics-data-analysis-ibm",
    }
    assert "unimas-excel-booster" not in ids(skill="excel", max_cost_myr=500)
    assert ids(provider_type="university")
    cheapest = client.get("/api/v1/pathway/catalogue", params={"skill": "python"}).json()["courses"]
    costs = [c["cost_myr"] for c in cheapest]
    assert costs == sorted(costs)
    assert client.get("/api/v1/pathway/catalogue", params={"format": "nope"}).status_code == 422
