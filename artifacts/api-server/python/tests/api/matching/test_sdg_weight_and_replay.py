"""SDG-weighted ranking and trend replay with reasons (F4 good-to-haves)."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.contracts.common import RecommendationMeta, Source
from app.contracts.matching import RoleMatch, ScoreComponent
from app.contracts.sdg import SdgLink, SdgTarget
from app.features.matching import replay_diff, sdg_weight
from app.features.matching.scoring import MatchProfile, Role, RoleSkill, Weights

AISYAH = {"X-Demo-User": "aisyah"}
META = RecommendationMeta(
    sources=[Source(name="t", url="https://example.test", retrieved_at=date(2026, 1, 1))],
    snapshot_date=date(2026, 1, 1),
    scenario="moderate",
)


def _link(goal: int, strength: str) -> SdgLink:
    target = SdgTarget(goal=goal, target=f"{goal}.1", label=f"Goal {goal}")
    return SdgLink(target=target, reason="r", strength=strength)  # type: ignore[arg-type]


def _match(role_id: str, value: float) -> RoleMatch:
    return RoleMatch(
        role_id=role_id,
        label=role_id,
        score=value,
        components=[ScoreComponent(name="skill_overlap", weight=1.0, value=value, explanation="x")],
        missing_skills=[],
        partial_skills=[],
        sdg_targets=[],
        meta=META,
    )


def test_impact_is_relative_and_counts_enabling_links_half() -> None:
    links = {"a": [_link(4, "direct"), _link(8, "direct")], "b": [_link(4, "enabling")], "c": []}
    impact = sdg_weight.sdg_impact(links, lambda rid: links[rid])
    assert impact == {"a": 1.0, "b": 0.25, "c": 0.0}


def test_weight_zero_keeps_ranking_and_weight_can_reorder() -> None:
    matches = [_match("high-fit", 0.8), _match("high-sdg", 0.6)]
    impact = {"high-fit": 0.0, "high-sdg": 1.0}
    assert sdg_weight.apply(matches, impact, 0) is matches
    reranked = sdg_weight.apply(matches, impact, 0.5)
    assert [m.role_id for m in reranked] == ["high-sdg", "high-fit"]
    top = reranked[0]
    assert abs(sum(c.weight for c in top.components) - 1.0) < 1e-6
    assert top.components[-1].name == "sdg_impact"
    assert abs(top.score - sum(c.weight * c.value for c in top.components)) < 1e-6


def test_replay_names_the_skills_that_moved_a_role() -> None:
    role = Role(
        role_id="r", skills=(RoleSkill("up", 1.0), RoleSkill("flat", 0.5), RoleSkill("down", 0.2))
    )
    found = replay_diff.drivers(
        role, {"up": 0.1, "flat": 0.3, "down": 0.5}, {"up": 0.9, "flat": 0.3, "down": 0.1}
    )
    assert [d.skill_id for d in found] == ["up", "down"]
    assert found[0].effect > 0 > found[1].effect
    rows = replay_diff.compare(
        MatchProfile(skills={"up": 3.0}),
        [role],
        {"up": 0.1, "flat": 0.3, "down": 0.5},
        {"up": 0.9, "flat": 0.3, "down": 0.1},
        Weights(),
    )
    assert rows[0][0].rank_before == rows[0][0].rank_after == 1


def test_api_sdg_weight_adds_a_visible_part(client: TestClient) -> None:
    base = client.get("/api/v1/matches", headers=AISYAH).json()["matches"]
    assert all(c["name"] != "sdg_impact" for c in base[0]["components"])
    weighted = client.get("/api/v1/matches", params={"sdg_weight": 0.6}, headers=AISYAH)
    assert weighted.status_code == 200, weighted.text
    first = weighted.json()["matches"][0]
    names = [c["name"] for c in first["components"]]
    assert names[-1] == "sdg_impact"
    assert abs(sum(c["weight"] for c in first["components"]) - 1.0) < 1e-3
    scores = [m["score"] for m in weighted.json()["matches"]]
    assert scores == sorted(scores, reverse=True)
    assert (
        client.get("/api/v1/matches", params={"sdg_weight": 1.5}, headers=AISYAH).status_code == 422
    )


def test_api_replay_explains_movements(client: TestClient) -> None:
    snap = client.get("/api/v1/trends/snapshot").json()
    dates = snap["meta"]["available_snapshots"]
    assert len(dates) >= 2
    resp = client.get("/api/v1/matches/replay", params={"from_date": dates[0]}, headers=AISYAH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["from_date"] == dates[0] and body["to_date"] == dates[-1]
    ranks = sorted(m["rank_after"] for m in body["movements"])
    assert ranks == list(range(1, len(ranks) + 1))
    assert body["meta"]["sources"]
    same = client.get("/api/v1/matches/replay", params={"from_date": dates[-1]}, headers=AISYAH)
    assert same.status_code == 422


def test_replay_driver_follows_percentile_not_raw_velocity() -> None:
    """A skill whose velocity rises while others rise faster loses position: a fall."""
    role = Role(role_id="r", skills=(RoleSkill("mine", 1.0),))
    before = {"mine": 0.5, "a": 0.1, "b": 0.2}
    after = {"mine": 0.6, "a": 0.9, "b": 0.8}  # mine went up, but is now the lowest
    (found,) = replay_diff.drivers(role, before, after)
    assert found.velocity_after > found.velocity_before
    assert found.position_after < found.position_before
    assert found.effect < 0
    rows = replay_diff.compare(MatchProfile(skills={}), [role], before, after, Weights())
    movement, drivers = rows[0]
    # The effect is exactly the change in score the skill caused.
    assert abs(drivers[0].effect - (movement.score_after - movement.score_before)) < 1e-3


def test_replay_applies_the_sdg_weight_to_both_snapshots() -> None:
    fit = Role(role_id="fit", skills=(RoleSkill("s", 1.0),))
    green = Role(role_id="green", skills=(RoleSkill("t", 1.0),))
    profile = MatchProfile(skills={"s": 3.0})
    v = {"s": 0.5, "t": 0.4}
    plain = replay_diff.compare(profile, [fit, green], v, v, Weights())
    assert plain[0][0].role_id == "fit"
    weighted = replay_diff.compare(
        profile, [fit, green], v, v, Weights(), impact={"fit": 0.0, "green": 1.0}, sdg_weight=0.9
    )
    top = weighted[0][0]
    assert top.role_id == "green" and top.rank_before == top.rank_after == 1


def test_api_detail_and_replay_keep_the_sdg_weight(client: TestClient) -> None:
    weighted = client.get("/api/v1/matches", params={"sdg_weight": 0.6}, headers=AISYAH).json()
    first = weighted["matches"][0]
    detail = client.get(
        f"/api/v1/matches/{first['role_id']}", params={"sdg_weight": 0.6}, headers=AISYAH
    ).json()
    assert abs(detail["score"] - first["score"]) < 1e-6
    dates = client.get("/api/v1/trends/snapshot").json()["meta"]["available_snapshots"]
    replay = client.get(
        "/api/v1/matches/replay",
        params={"from_date": dates[0], "sdg_weight": 0.6},
        headers=AISYAH,
    ).json()
    assert [m["role_id"] for m in replay["movements"]] == [
        m["role_id"] for m in weighted["matches"]
    ]


def test_api_outlook_for_an_older_snapshot_cites_that_snapshot(client: TestClient) -> None:
    dates = client.get("/api/v1/trends/snapshot").json()["meta"]["available_snapshots"]
    roles = client.get("/api/v1/matches", headers=AISYAH).json()["matches"]
    resp = client.get(
        "/api/v1/scenarios/outlook",
        params={"role_id": roles[0]["role_id"], "snapshot_date": dates[0]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["meta"]["snapshot_date"] == dates[0]
    missing = client.get(
        "/api/v1/scenarios/outlook",
        params={"role_id": roles[0]["role_id"], "snapshot_date": "1999-01-01"},
    )
    assert missing.status_code == 404


def test_ranking_explanation_says_how_many_links_are_drafts() -> None:
    draft = _link(4, "direct")
    reviewed = _link(8, "direct").model_copy(update={"reviewed": True})
    assert sdg_weight.review_note([draft, reviewed]).startswith("1 of 2 links were reviewed")
    assert sdg_weight.review_note([reviewed]) == "All 1 links were reviewed by a person."
    (m,) = sdg_weight.apply([_match("a", 0.5)], {"a": 1.0}, 0.5, {"a": "1 of 2 reviewed."})
    assert m.components[-1].explanation.endswith("1 of 2 reviewed.")
    assert "reviewed links" not in m.components[-1].explanation
