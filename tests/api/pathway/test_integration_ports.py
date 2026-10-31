"""Pathway reads M1's trend snapshot, has one gap rule."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import Source
from app.contracts.pathway import Pathway
from app.contracts.sdg import SdgContribution
from app.features.pathway import data, engine, service, trend_port

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


def test_uses_shared_weighted_snapshot_when_m1_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.features.trends import service as trends_service

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("trend layer down")

    monkeypatch.setattr(trends_service, "get_snapshot", boom)
    view = trend_port.current("fast")
    assert view is not None and view.is_m1 and view.scenario_weighted
    fallback = trends_service.last_good_snapshot(None, "fast")
    assert view.snapshot.is_fallback and view.snapshot.served_from == fallback.meta.served_from
    assert view.growth == {item.skill_id: item.velocity_fast for item in fallback.items}


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


# --- retired comparison route -------------------------------------------------------------


def test_comparison_endpoint_is_removed(client: TestClient) -> None:
    assert client.get("/api/v1/pathway/compare", headers=AISYAH).status_code == 404
    assert "/api/v1/pathway/compare" not in client.app.openapi()["paths"]


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
