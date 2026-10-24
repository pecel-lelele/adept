"""Tests for Prompt 4: unified skills-gap rule and live SDG badges.

Rules tested:
1. Role needs Python level 2, user has level 2: state 'have', credit 1.0.
2. Role needs level 4, user has level 2: state 'partial', credit 0.5.
3. Skill not in the profile: state 'missing', credit 0.
4. Overlap score and gap output are consistent for the same inputs.
5. Role badges equal the SDG service output for two demo roles.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.features.matching.scoring import (
    MatchProfile,
    Role,
    RoleSkill,
    gap_state,
    skill_credit,
    skill_overlap,
    skills_gap,
)
from app.features.sdg import service as sdg_service

# ---------------------------------------------------------------------------
# Tests 1-3: Unit rules for credit and gap state
# ---------------------------------------------------------------------------


def test_role_needs_level_2_user_has_level_2() -> None:
    """Role needs Python level 2, user has level 2: state 'have', credit 1.0."""
    state = gap_state(user_level=2, required_level=2)
    credit = skill_credit(user_level=2, required_level=2)

    assert state == "have"
    assert credit == pytest.approx(1.0)


def test_role_needs_level_4_user_has_level_2() -> None:
    """Role needs level 4, user has level 2: state 'partial', credit 0.5."""
    state = gap_state(user_level=2, required_level=4)
    credit = skill_credit(user_level=2, required_level=4)

    assert state == "partial"
    assert credit == pytest.approx(0.5)


def test_skill_not_in_profile() -> None:
    """Skill not in the profile: 'missing', credit 0."""
    state = gap_state(user_level=0, required_level=3)
    credit = skill_credit(user_level=0, required_level=3)

    assert state == "missing"
    assert credit == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 4: Overlap score and gap output are consistent for the same inputs
# ---------------------------------------------------------------------------


def test_overlap_and_gap_consistency() -> None:
    """Overlap score and gap output must never disagree for the same inputs."""
    role = Role(
        role_id="test-role",
        skills=(
            RoleSkill("sql", importance=1.0, required_level=3),
            RoleSkill("python", importance=0.8, required_level=2),
            RoleSkill("excel", importance=0.5, required_level=4),
        ),
    )
    profile = MatchProfile(
        skills={
            "sql": 3,  # user 3 >= req 3 -> have, credit 1.0
            "python": 1,  # 0 < user 1 < req 2 -> partial, credit 0.5
            # excel missing -> missing, credit 0.0
        }
    )

    gap = skills_gap(profile, role)

    assert set(gap["have"]) == {"sql"}
    assert set(gap["partial"]) == {"python"}
    assert set(gap["missing"]) == {"excel"}

    # Overlap score calculation:
    # sql: 1.0 * 1.0 = 1.0
    # python: 0.8 * 0.5 = 0.4
    # excel: 0.5 * 0.0 = 0.0
    # total weight = 1.0 + 0.8 + 0.5 = 2.3
    # expected overlap = 1.4 / 2.3 = 0.60869565...
    expected_overlap = (1.0 * 1.0 + 0.8 * 0.5 + 0.5 * 0.0) / (1.0 + 0.8 + 0.5)
    overlap = skill_overlap(profile, role)

    assert overlap == pytest.approx(expected_overlap)

    # Consistency guarantee across all role skills:
    for rs in role.skills:
        u_lvl = profile.skills.get(rs.skill_id, 0)
        c = skill_credit(u_lvl, rs.required_level)
        if rs.skill_id in gap["have"]:
            assert c == pytest.approx(1.0)
        elif rs.skill_id in gap["partial"]:
            assert 0.0 < c < 1.0
        elif rs.skill_id in gap["missing"]:
            assert c == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 5: Role badges equal the SDG service output for two demo roles
# ---------------------------------------------------------------------------


def test_role_badges_equal_sdg_service_output(client: TestClient) -> None:
    """Role badges on matching response must equal sdg.service.role_badges()."""
    # Use standard demo user "aisyah"
    resp = client.get("/api/v1/matches", params={"scenario": "moderate"})
    assert resp.status_code == 200
    body = resp.json()

    matches = {m["role_id"]: m for m in body["matches"]}

    for role_id in ("data-analyst", "ai-operations-specialist"):
        assert role_id in matches, f"Role {role_id} missing from matches"
        match_sdgs = matches[role_id]["sdg_targets"]
        expected_sdgs = [
            {"goal": t.goal, "target": t.target, "label": t.label}
            for t in sdg_service.role_badges(role_id)
        ]

        assert match_sdgs == expected_sdgs, (
            f"SDG targets mismatch for {role_id}:\n"
            f"Matching: {match_sdgs}\n"
            f"SDG Service: {expected_sdgs}"
        )
