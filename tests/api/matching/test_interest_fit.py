"""Interest bonus and API arithmetic use the same neutral-plus-overlap formula (M2-030)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.features.matching import repository
from app.features.matching.scoring import (
    NEUTRAL,
    MatchProfile,
    Role,
    RoleSkill,
    Weights,
    interest_fit,
    score_role,
)
from app.features.profile import repository as profile_repo


def _make_role(role_id: str, tags: set[str]) -> Role:
    return Role(
        role_id=role_id,
        skills=(RoleSkill(skill_id="python", importance=1.0, required_level=2),),
        interest_tags=frozenset(tags),
    )


def test_extra_role_tags_do_not_dilute_a_matching_interest() -> None:
    """All declared interests match, regardless of unused role tags."""
    profile = MatchProfile(skills={"python": 0.5}, interests=frozenset({"tech"}))
    role = _make_role("role-1", {"tech", "fin", "green", "health", "ai"})

    fit = interest_fit(profile, role)
    assert fit == pytest.approx(1.0)


def test_identical_sets_give_one() -> None:
    """User {tech, fin} vs role {tech, fin} gives 1.0."""
    profile = MatchProfile(skills={"python": 0.5}, interests=frozenset({"tech", "fin"}))
    role = _make_role("role-2", {"tech", "fin"})

    fit = interest_fit(profile, role)
    assert fit == pytest.approx(1.0)


def test_disjoint_sets_give_neutral() -> None:
    """Unmatched interests cannot lower the score below no interests."""
    profile = MatchProfile(skills={"python": 0.5}, interests=frozenset({"tech"}))
    role = _make_role("role-3", {"finance", "legal"})

    fit = interest_fit(profile, role)
    assert fit == pytest.approx(NEUTRAL)


def test_empty_user_interests_give_none_and_neutral_contribution() -> None:
    """Empty user interests give None and a neutral contribution of 0.5 in the total."""
    profile = MatchProfile(skills={"python": 1.0}, interests=frozenset())
    role = Role(
        role_id="role-4",
        skills=(RoleSkill(skill_id="python", importance=1.0, required_level=1),),
        interest_tags=frozenset({"tech", "fin"}),
    )

    # interest_fit alone returns None (not provided)
    fit = interest_fit(profile, role)
    assert fit is None

    # score_role applies the neutral contribution in the total score
    w = Weights()  # production defaults (M2-011)
    scores = {"python": 1.0}  # skill overlap = 1.0, trend = 1.0
    expected = w.skill * 1.0 + w.trend * 1.0 + w.interest * NEUTRAL
    result = score_role(profile, role, scores, w)
    assert result.breakdown["interest"] is None
    assert result.score == pytest.approx(expected)


# ---------------------------------------------------------------------------
# API surface: the breakdown must expose None as "not provided"
# ---------------------------------------------------------------------------

USER_HEADER = {"X-Demo-User": "weijie"}


@pytest.fixture(autouse=True)
def _isolate_profile_store():
    saved = {k: v.model_copy(deep=True) for k, v in profile_repo._store.items()}
    profile_repo._store.clear()
    yield
    profile_repo._store.clear()
    profile_repo._store.update(saved)


def _interest_component(match_body: dict) -> dict:
    return next(c for c in match_body["components"] if c["name"] == "interest_fit")


def test_api_interest_is_marked_not_provided(client: TestClient) -> None:
    """Skills but no interests -> provided=false, neutral value, text says not provided."""
    assert (
        client.put(
            "/api/v1/profile/skills/confirm",
            json={"skills": [{"skill_id": "python", "level": 5}]},
            headers=USER_HEADER,
        ).status_code
        == 200
    )

    resp = client.get("/api/v1/matches", params={"scenario": "moderate"}, headers=USER_HEADER)
    assert resp.status_code == 200, resp.text
    comp = _interest_component(resp.json()["matches"][0])
    assert comp["provided"] is False
    assert comp["value"] == pytest.approx(NEUTRAL)
    assert "not provided" in comp["explanation"].lower()

    # the total counts the neutral value for the interest weight (weights read from the payload)
    match = resp.json()["matches"][0]
    weight = {c["name"]: c["weight"] for c in match["components"]}
    numeric = {c["name"]: c["value"] for c in match["components"]}
    expected = (
        weight["skill_overlap"] * numeric["skill_overlap"]
        + weight["trend_outlook"] * numeric["trend_outlook"]
        + weight["interest_fit"] * NEUTRAL
    )
    assert match["score"] == pytest.approx(expected, abs=1e-3)


def test_api_interest_bonus_when_provided(client: TestClient) -> None:
    """Given interests -> provided=true and value uses neutral plus matched share."""
    q = client.post(
        "/api/v1/profile/questionnaire",
        json={
            "segment": "graduate",
            "interests": ["data", "age", "gender"],
            "hours_per_week": 10,
            "learning_style": "mixed",
            "budget_myr": 100,
            "hrd_eligible": False,
        },
        headers=USER_HEADER,
    )
    assert q.status_code == 200, q.text
    # intake sanitising reaches the stored profile: only the non-demographic tag survives
    assert q.json()["interests"] == ["data"]
    assert (
        client.put(
            "/api/v1/profile/skills/confirm",
            json={"skills": [{"skill_id": "python", "level": 5}]},
            headers=USER_HEADER,
        ).status_code
        == 200
    )

    resp = client.get("/api/v1/matches", params={"scenario": "moderate"}, headers=USER_HEADER)
    assert resp.status_code == 200, resp.text
    user_interests = frozenset({"data"})  # what survived sanitising above
    for m in resp.json()["matches"]:
        comp = _interest_component(m)
        assert comp["provided"] is True
        tags = {tag.casefold() for tag in repository.role_interest_tags(m["role_id"])}
        expected = NEUTRAL + (1 - NEUTRAL) * len(user_interests & tags) / len(user_interests)
        assert comp["value"] == pytest.approx(expected, abs=1e-4), m["role_id"]
        assert "case-insensitive" in comp["explanation"]
        assert m["score"] == pytest.approx(sum(c["weight"] * c["value"] for c in m["components"]))
