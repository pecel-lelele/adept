"""Catalogue graph invariants and prerequisite safety across the expanded role pool."""

import json
from dataclasses import replace
from pathlib import Path

from app.core import taxonomy
from app.features.matching import repository as matching
from app.features.pathway import data, engine, service
from app.features.profile import cv_parser


def test_catalogue_entities_form_a_closed_sourced_graph():
    skills = set(data.skill_labels())
    roles = set(data.role_labels())
    courses = data.catalogue()
    assert len(skills) >= 140 and len(roles) >= 31 and len(courses) >= 71
    assert {r.role_id for r in matching.load_roles()} == set(data.target_role_ids())
    for role in data.target_role_ids():
        assert {r.skill_id for r in data.requirements(role)} <= skills
        assert any(
            set(c.skill_ids) & {r.skill_id for r in data.requirements(role)} for c in courses
        )
    for course in courses:
        assert set(course.skill_ids) <= skills
        assert course.source and course.source.url.startswith("https://")
    for skill, prerequisites in data.prerequisites().items():
        assert skill in skills and set(prerequisites) <= skills
    provenance = Path(__file__).resolve().parents[3] / "src/data/seed/taxonomy/provenance.json"
    source = json.loads(provenance.read_text(encoding="utf-8"))
    assert {r["role_id"] for r in source["roles"]} == roles
    assert all(
        r["occupation_code"] and r["source_url"].startswith("https://www.onetonline.org/")
        for r in source["roles"]
    )


def test_legacy_skill_credit_is_shared_without_double_counting():
    assert taxonomy.levels(
        {"excel": 2, "excel-basic": 4, "rpa": 1, "robotic-process-automation": 3}
    ) == {"excel": 4, "rpa": 3}
    gaps = service.skills_gap({"robotic-process-automation": 3}, "process-automation-analyst")
    assert "rpa" in gaps["have"]
    extracted = cv_parser.extract_skills("Robotic process automation and Microsoft Excel")
    ids = [s.skill_id for s in extracted]
    assert "robotic-process-automation" not in ids and "excel-basic" not in ids


def test_missing_foundation_blocks_advanced_course_even_outside_role_requirements():
    from datetime import date

    from app.contracts.pathway import Course

    course = Course(
        id="synthetic-advanced",
        title="Synthetic advanced",
        provider="Synthetic",
        url="https://example.com/synthetic-course",
        hours=1,
        cost_myr=0,
        hrd_claimable=False,
        verified_at=date(2026, 10, 23),
        skill_ids=["advanced"],
        level=3,
    )
    plan = engine.build(
        [data.Requirement("advanced", 3, 1)],
        engine.Learner({}, 5, 0, False),
        "moderate",
        [course],
        {"advanced": {"foundation": "Synthetic prerequisite"}},
        {},
        {},
    )
    assert plan.steps == []
    unmet = {u.skill_id: u.reason for u in plan.unmet}
    assert unmet == {"foundation": "no_catalogue_course", "advanced": "blocked_prerequisite"}


def test_team_preserves_known_foundation_and_assigns_only_members_missing_it():
    members = {
        "synthetic-one": engine.Learner({"sql": 2}, 5, 0, False),
        "synthetic-two": engine.Learner({"sql": 2}, 5, 0, False),
    }
    plan = service.group_pathway(members, "digital-marketing-specialist", "moderate", False)
    assert "sql" not in {s.skill_id for s in plan.steps}
    assert all(s.member_ids for s in plan.steps)
    members["synthetic-two"] = engine.Learner({}, 5, 0, False)
    partial = service.group_pathway(members, "digital-marketing-specialist", "moderate", False)
    foundation = next(s for s in partial.steps if s.skill_id == "sql")
    assert foundation.member_ids == ["synthetic-two"]


def test_multi_skill_course_avoids_lower_foundation_and_keeps_remaining_gap():
    courses = data.catalogue()
    # ai-ethics is asked at level 4 here so a gap remains after the level-2/3 courses,
    # whatever level the seed role currently requires.
    plan = engine.build(
        [
            replace(r, required_level=4) if r.skill_id == "ai-ethics" else r
            for r in data.requirements("compliance-analytics-officer")
            if r.skill_id in {"data-privacy", "ai-ethics"}
        ],
        engine.Learner({}, 5, 0, False),
        "moderate",
        courses,
        data.prerequisites(),
        {},
        data.skill_labels(),
    )
    chosen = {c.id for step in plan.steps for c in step.courses}
    assert "mslearn-ai-privacy" in chosen
    assert "mslearn-responsible-copilot" not in chosen
    ethics = next(step for step in plan.steps if step.skill_id == "ai-ethics")
    assert ethics.reaches_level >= 2
    assert "mslearn-ai-privacy" in {c.id for c in ethics.courses}
    unique = {c.id: c for step in plan.steps for c in step.courses}
    assert plan.total_hours == round(sum(c.hours for c in unique.values()), 1)
    assert plan.total_cost_myr == round(sum(c.cost_myr for c in unique.values()), 2)
    assert {u.skill_id for u in plan.unmet} == {"ai-ethics"}
