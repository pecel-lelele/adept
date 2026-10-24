"""Pathway reads M1's trend snapshot, compares roles before choosing, and has one gap rule."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import Source
from app.contracts.pathway import Pathway, RoleComparison
from app.contracts.sdg import SdgContribution
from app.features.pathway import data, engine, service, trend_port
from app.features.sdg import repository as sdg_repository
from app.features.sdg import service as sdg_service

AISYAH = {"X-Demo-User": "aisyah"}


def _view(growth: dict[str, float], version: str = "m1-2026-11-01") -> trend_port.TrendView:
    src = Source(name="SYNTHETIC M1", url="https://example.org", retrieved_at=date(2026, 11, 1))
    return trend_port.TrendView(
        snapshot=data.Snapshot(version, version, src, (src,)),
        growth=growth,
        scenario_weighted=True,
        available_dates=(date(2026, 10, 20), date(2026, 11, 1)),
    )


# --- trend adapter ------------------------------------------------------------------------


def test_uses_m1_snapshot_when_it_has_data() -> None:
    view = trend_port.current("moderate")
    assert view is not None and view.is_m1 and view.scenario_weighted
    assert {s.name for s in view.snapshot.all_sources()} != {"MOCK DATA"}
    assert view.growth and view.available_dates


def test_falls_back_to_seed_snapshot_when_m1_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.features.trends import service as trends_service

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("trend layer down")

    monkeypatch.setattr(trends_service, "get_snapshot", boom)
    view = trend_port.current("fast")
    assert view is not None and not view.is_m1 and not view.scenario_weighted


def test_m1_velocity_is_not_weighted_twice() -> None:
    assert engine.trend_multiplier(0.3, "fast", scenario_weighted=True) == pytest.approx(1.3)
    assert engine.trend_multiplier(0.3, "fast") == pytest.approx(1.6)


def test_pathway_cites_m1_sources_and_flags_unscored_skills(client: TestClient) -> None:
    resp = client.get(
        "/api/v1/pathway", params={"role_id": "process-automation-analyst"}, headers=AISYAH
    )
    plan = Pathway.model_validate(resp.json())
    view = trend_port.current("moderate")
    assert view and plan.snapshot_version == view.snapshot.version
    assert {s.name for s in view.snapshot.all_sources()} <= {s.name for s in plan.meta.sources}
    missing = view.uncovered([g.skill_id for g in plan.gaps])
    if missing:
        assert any("no signal" in w for w in plan.warnings)


def test_trend_change_reorders_the_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    learner = engine.Learner({}, hours_per_week=6, budget_myr=500, hrd_eligible=True)
    role = "process-automation-analyst"
    low = service.build_pathway(learner, role, "moderate", trend=_view({"python": -0.5}))
    high = service.build_pathway(learner, role, "moderate", trend=_view({"python": 1.0}))
    rank = {p: [s.skill_id for s in plan.steps] for p, plan in (("low", low), ("high", high))}
    assert rank["high"].index("python") < rank["low"].index("python")


def test_unknown_replay_date_is_404(client: TestClient) -> None:
    resp = client.get(
        "/api/v1/pathway",
        params={"role_id": "data-analyst", "snapshot_date": "1999-01-01"},
        headers=AISYAH,
    )
    assert resp.status_code == 404


# --- compare before choosing --------------------------------------------------------------


def test_compare_lists_every_target_role_with_f6_badges(client: TestClient) -> None:
    resp = client.get("/api/v1/pathway/compare", headers=AISYAH)
    assert resp.status_code == 200, resp.text
    body = RoleComparison.model_validate(resp.json())
    assert [o.role_id for o in body.options] == data.target_role_ids()
    assert body.meta.is_estimate and body.meta.sources and body.snapshot_version
    for option in body.options:
        f6 = [link.target for link in sdg_repository.role_links(option.role_id)]
        assert option.sdg_targets == f6 == sdg_service.role_badges(option.role_id)
        assert 0 <= option.trend_coverage <= 1
        if option.trend_signal is None:
            assert option.trend_direction == "unknown"


def test_compare_filters_roles_and_marks_the_saved_choice(client: TestClient) -> None:
    client.post(
        "/api/v1/pathway/plans",
        json={"role_id": "data-analyst", "scenario": "moderate"},
        headers=AISYAH,
    )
    resp = client.get(
        "/api/v1/pathway/compare",
        params=[("role_ids", "data-analyst"), ("role_ids", "nope"), ("role_ids", "data-analyst")],
        headers=AISYAH,
    )
    body = RoleComparison.model_validate(resp.json())
    assert [o.role_id for o in body.options] == ["data-analyst"]
    assert body.saved_role_id == "data-analyst" and body.options[0].is_saved_choice


def test_role_trend_is_importance_weighted_over_covered_skills() -> None:
    reqs = [data.Requirement("a", 3, 1.0), data.Requirement("b", 3, 1.0)]
    signal, coverage = service.role_trend(reqs, _view({"a": 0.4}))
    assert signal == pytest.approx(0.4) and coverage == pytest.approx(0.5)
    assert service.role_trend(reqs, _view({})) == (None, 0.0)


# --- one gap rule -------------------------------------------------------------------------


def test_skills_gap_compares_against_the_required_level() -> None:
    gap = service.skills_gap({"process-mapping": 2, "python": 2}, "process-automation-analyst")
    assert "process-mapping" in gap["partial"]  # level 2 of 3 is partial, not missing
    assert "python" in gap["have"]  # the role needs level 2
    assert "rpa" in gap["missing"]


# --- SDG contribution never assumes a role ------------------------------------------------


def test_sdg_contribution_without_a_chosen_role_is_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/sdg/contribution/me", headers=AISYAH)
    body = SdgContribution.model_validate(resp.json())
    assert body.role_ids == [] and body.links == []
