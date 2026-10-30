"""N3: role directions on the radar carry trend coverage and flag thin evidence."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.features.pathway import data as pathway_data
from app.features.trends import mocks, service


def test_every_role_signal_has_coverage_and_the_flag_follows_it(client: TestClient) -> None:
    body = client.get("/api/v1/trends/radar", params={"scenario": "moderate"}).json()
    roles = [s for s in body["items"] if s["entity_type"] == "role"]
    assert roles
    for role in roles:
        assert 0 < role["trend_coverage"] <= 1
        assert role["insufficient_evidence"] is (role["trend_coverage"] < 0.5)
    for skill in (s for s in body["items"] if s["entity_type"] == "skill"):
        assert skill["trend_coverage"] is None
        assert skill["insufficient_evidence"] is False


def test_coverage_is_the_share_of_role_importance_with_trend_data() -> None:
    snap = mocks.snapshot("moderate")
    scored = {i.skill_id for i in snap.items}
    signals = {
        s.entity_id: s
        for s in service.signals_from_snapshot(snap, "moderate")
        if s.entity_type == "role"
    }
    for role_id, signal in signals.items():
        reqs = pathway_data.requirements(role_id)
        total = sum(r.importance for r in reqs)
        covered = sum(r.importance for r in reqs if r.skill_id in scored)
        assert signal.trend_coverage == round(covered / total, 4)


def test_a_thinly_covered_role_is_marked_insufficient() -> None:
    snap = mocks.snapshot("moderate")
    scored = {i.skill_id for i in snap.items}
    for role_id in pathway_data.target_role_ids():
        reqs = sorted(pathway_data.requirements(role_id), key=lambda r: r.importance)
        total = sum(r.importance for r in reqs)
        if len(reqs) > 1 and reqs[0].skill_id in scored and reqs[0].importance / total < 0.5:
            break
    else:
        raise AssertionError("no role with a minor scored requirement")
    dropped = {r.skill_id for r in reqs[1:]}  # only the least important one keeps trend data
    thin = snap.model_copy(update={"items": [i for i in snap.items if i.skill_id not in dropped]})
    signal = next(
        s for s in service.signals_from_snapshot(thin, "moderate") if s.entity_id == role_id
    )
    assert signal.trend_coverage is not None and signal.trend_coverage < 0.5
    assert signal.insufficient_evidence is True
