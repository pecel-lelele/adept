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
