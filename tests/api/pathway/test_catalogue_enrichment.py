"""Issue #56: sourced digital/current occupations form a consistent catalogue graph."""

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import Source
from app.core import seed
from app.features.matching import repository as matching
from app.features.pathway import data, engine, service, trend_port
from app.features.sdg import repository as sdg

TECH_ROLES = {
    "web-developers",
    "database-administrators",
    "network-systems-administrators",
    "software-quality-assurance-testers",
    "business-intelligence-analysts",
}


def test_seed_graph_has_unique_ids_and_no_dangling_edges() -> None:
    for area, table in (("taxonomy", "roles"), ("taxonomy", "skills"), ("courses", "courses")):
        ids = [row["id"] for row in seed.rows(area, table)]
        assert len(ids) == len(set(ids)), (area, table)
    roles = set(data.role_labels())
    skills = set(data.skill_labels())
    for area, table, keys in (
        ("taxonomy", "role_skills", ("role_id", "skill_id")),
        ("sdg", "role_sdg_map", ("role_id", "sdg_target_id")),
        ("sdg", "skill_sdg_map", ("skill_id", "sdg_target_id")),
    ):
        edges = [tuple(row[key] for key in keys) for row in seed.rows(area, table)]
        assert len(edges) == len(set(edges)), table
    for row in seed.rows("taxonomy", "role_skills"):
        assert row["role_id"] in roles and row["skill_id"] in skills
        assert 1 <= int(row["required_level"]) <= 5 and 0 < float(row["importance"]) <= 1
    for row in seed.rows("sdg", "role_sdg_map"):
        assert row["role_id"] in roles and row["sdg_target_id"] in sdg.targets()
    for row in seed.rows("sdg", "skill_sdg_map"):
        assert row["skill_id"] in skills and row["sdg_target_id"] in sdg.targets()


def test_official_occupation_titles_and_digital_skills_resolve_to_dated_sources() -> None:
    manifest = json.loads((seed.SEED_DIR / "taxonomy/provenance.json").read_text(encoding="utf-8"))
    sources = {row["role_id"]: row for row in manifest["roles"]}
    assert len(sources) == len(manifest["roles"])
    for role in seed.rows("taxonomy", "roles"):
        source = sources[role["id"]]
        assert role["taxonomy"] == "O*NET-SOC"
        assert role["label"] == source["occupation_title"] == source["label"]
        assert source["source_url"].endswith(source["occupation_code"])
        assert source["retrieved_at"] in {"2026-10-30", "2026-10-31"}
        assert source["requirements_basis"]
    assert {row["skill_id"] for row in manifest["skills"]} == {"git", "selenium"}
    assert TECH_ROLES <= {role.role_id for role in matching.load_roles()}
    assert not {
        "retail-salespersons",
        "customer-service-representatives",
        "team-assemblers",
        "registered-nurses",
        "bank-tellers",
    } & {role.role_id for role in matching.load_roles()}
    assert data.requirements("team-assemblers")
    # O*NET has no detailed requirements for this aggregate; keep the absence explicit.
    assert not data.requirements("production-workers-all-other")
    assert data.taxonomy_source().retrieved_at.isoformat() == manifest["snapshot_date"]


@pytest.mark.parametrize("role_id", sorted(TECH_ROLES))
def test_untracked_tech_skills_are_unknown_and_unavailable_courses_stay_unmet(role_id: str) -> None:
    source = Source(
        name="Synthetic empty signal", url="https://example.test", retrieved_at="2026-10-20"
    )
    view = trend_port.TrendView(data.Snapshot("synthetic", "synthetic", source), {}, True)
    assert service.role_trend(data.requirements(role_id), view) == (None, 0.0)
    plan = service.build_pathway(
        engine.Learner({}, 5, 1000, False), role_id, "moderate", trend=view
    )
    assert any("no signal" in warning and "neutral" in warning for warning in plan.warnings)
    if role_id == "software-quality-assurance-testers":
        assert any(
            g.skill_id == "selenium" and g.reason == "no_catalogue_course" for g in plan.unmet
        )


def test_malay_courses_and_tech_sdg_links_preserve_dated_attribution(client: TestClient) -> None:
    response = client.get("/api/v1/pathway/catalogue")
    assert response.status_code == 200
    courses = {course["id"]: course for course in response.json()["courses"]}
    for row in seed.rows("courses", "courses"):
        if row["language"] == "ms":
            course = courses[row["id"]]
            assert course["verified_at"] == course["source"]["retrieved_at"] == "2026-10-30"
            assert course["source"]["url"] == row["url"] and course["duration_note"]
    for role in TECH_ROLES:
        links = sdg.role_links(role)
        assert {link.target.target for link in links} == {"4.4", "8.2"}
        assert all(not link.reviewed and link.strength == "enabling" for link in links)
        assert all(
            link.evidence and link.evidence.source.retrieved_at == date(2026, 10, 30)
            for link in links
        )
    # Reopening target 4.4 evidence does not refresh unrelated evidence dates.
    old = next(
        link for link in sdg.role_links("bank-operations-executive") if link.target.target == "8.10"
    )
    assert old.evidence and old.evidence.source.retrieved_at == date(2026, 10, 20)
