"""Catalogue graph invariants and prerequisite safety across the expanded role pool."""

import json
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
    provenance = Path("src/data/seed/taxonomy/provenance.json")
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
