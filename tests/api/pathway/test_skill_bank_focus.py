"""Digital/green requirements and dated course evidence for issue #84."""

import json
from datetime import date

from fastapi.testclient import TestClient

from app.core import seed, taxonomy
from app.features.pathway import data, engine, service

OUT_OF_SCOPE = {
    "stakeholder-management",
    "coaching-mentoring",
    "public-speaking",
    "cross-cultural-communication",
    "critical-thinking",
    "change-management",
    "patient-care",
    "clinical-judgement",
}
DIGITAL_GAPS = {
    "cloud-ai-services",
    "enterprise-architecture",
    "explainable-ai",
    "ai-safety",
    "bias-auditing",
    "security-ai",
    "ai-product-management",
    "fintech-ai",
    "financial-analysis",
    "precision-agriculture",
    "climate-ai",
    "regulatory-affairs",
    "sql-advanced",
    "selenium",
    "workforce-planning",
    "learning-development",
}


def test_targets_only_require_in_scope_skills_but_intake_keeps_existing_skills() -> None:
    for role in data.target_role_ids():
        requirements = data.requirements(role)
        assert requirements and not OUT_OF_SCOPE & {r.skill_id for r in requirements}, role
        assert all(0 < r.importance <= 1 for r in requirements)
    assert OUT_OF_SCOPE <= data.skill_labels().keys()
    assert {"patient-care", "clinical-judgement"} <= {
        r.skill_id for r in data.requirements("registered-nurses")
    }
    assert {r.skill_id for r in data.requirements("digital-health-nurse")} == {
        "healthcare-informatics",
        "ai-literacy",
    }


def test_every_target_requirement_has_a_catalogue_entry_without_claiming_level_closure() -> None:
    offered = {taxonomy.canonical(s) for c in data.catalogue() for s in c.skill_ids}
    for role in data.target_role_ids():
        assert {taxonomy.canonical(r.skill_id) for r in data.requirements(role)} <= offered, role
    assert DIGITAL_GAPS <= offered
    # The introductory finance masterclass must not pretend to satisfy level-3 finance AI.
    plan = engine.build(
        [data.Requirement("fintech-ai", 3, 1)],
        engine.Learner({}, 5, 0, False),
        "moderate",
        data.catalogue(),
        {},
        {},
        data.skill_labels(),
    )
    assert any(u.skill_id == "fintech-ai" for u in plan.unmet)


def test_skill_bank_course_facts_have_dated_provider_evidence_and_reach_the_api(
    client: TestClient,
) -> None:
    manifest = json.loads(
        (seed.SEED_DIR / "courses/skill_bank_provenance.json").read_text(encoding="utf-8")
    )
    entries = manifest["courses"]
    assert entries and len({r["course_id"] for r in entries}) == len(entries)
    response = client.get("/api/v1/pathway/catalogue")
    assert response.status_code == 200
    courses = {c["id"]: c for c in response.json()["courses"]}
    covered = set()
    for record in entries:
        course = courses[record["course_id"]]
        assert course["title"] == record["title"]
        assert course["url"] == record["url"]
        assert course["provider"] == record["provider"]
        assert course["hours"] == record["hours"]
        assert course["level"] == record["estimated_level"]
        assert course["cost_myr"] == 0 and not course["hrd_claimable"]
        assert course["verified_at"] == course["source"]["retrieved_at"] == record["opened_at"]
        assert date.fromisoformat(record["opened_at"]) <= date.today()
        assert course["source"]["url"] == record["source_url"]
        assert record["duration_evidence"] and record["price_evidence"] and record["skill_mapping"]
        assert course["duration_note"] and course["price_note"]
        covered.update(course["skill_ids"])
    assert DIGITAL_GAPS <= covered


def test_selenium_is_a_real_course_but_a_missing_catalogue_still_stays_unmet() -> None:
    plan = service.build_pathway(
        engine.Learner({"python": 3}, 5, 0, False),
        "software-quality-assurance-testers",
        "moderate",
    )
    assert any(c.id == "freecodecamp-selenium-bot" for step in plan.steps for c in step.courses)
    missing = engine.build(
        [data.Requirement("selenium", 2, 1)],
        engine.Learner({}, 5, 0, False),
        "moderate",
        [],
        {},
        {},
        data.skill_labels(),
    )
    assert [(u.skill_id, u.reason) for u in missing.unmet] == [("selenium", "no_catalogue_course")]
