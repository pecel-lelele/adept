"""Impact evidence: every displayed number must be derived from data, never typed in."""

import ast
import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import RecommendationMeta
from app.contracts.impact import EvidenceItem
from app.features.impact import service
from app.features.matching import repository as matching_repository
from app.features.matching.scoring import MatchProfile
from app.features.pathway import data as pathway_data
from app.features.pathway import engine
from app.features.pathway import service as pathway_service

SERVICE_FILE = Path(service.__file__)
URL = "/api/v1/impact/summary"


def _persona_learner(p: service.Persona) -> engine.Learner:
    return engine.Learner(dict(p.skills), p.hours_per_week, p.budget_myr, p.hrd_eligible)


def test_summary_is_public_and_carries_dated_sources(client: TestClient) -> None:
    resp = client.get(URL)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    meta = RecommendationMeta.model_validate(body["meta"])
    assert meta.is_estimate and meta.sources
    assert all(s.name and s.url and s.retrieved_at for s in meta.sources)
    assert body["persona_note"] == (
        f"Computed on {len(body['personas'])} synthetic personas from the live catalogue and "
        "trend snapshot; no human trials."
    )
    assert set(body["formulas"]) >= {"free_share", "fairness", "scenario"}


def test_free_share_matches_a_recount_from_the_catalogue(client: TestClient) -> None:
    persona = service.load_personas()[0]
    row = next(
        p for p in client.get(URL).json()["personas"] if p["persona_id"] == persona.persona_id
    )
    shown = row["moderate"]
    plan = pathway_service.build_pathway(
        _persona_learner(persona), shown["top_role_id"], "moderate"
    )
    ids = {c.id for s in plan.steps for c in s.courses}
    catalogue = pathway_data.course_index()
    courses = [catalogue[i] for i in ids]
    assert shown["course_count"] == len(courses)
    assert shown["free_course_share"] == round(
        sum(c.cost_myr == 0 for c in courses) / len(courses), 4
    )
    assert shown["total_hours"] == round(sum(c.hours for c in courses), 1)


def test_figures_follow_the_catalogue(monkeypatch: pytest.MonkeyPatch) -> None:
    before = service.compute_summary()
    assert before.aggregates[0].median_free_course_share > 0
    priced = [c.model_copy(update={"cost_myr": 10.0}) for c in pathway_data.catalogue()]
    monkeypatch.setattr(pathway_data, "catalogue", lambda: priced)
    after = service.compute_summary()
    assert after.aggregates[0].median_free_course_share == 0


def test_fairness_figure_is_measured_not_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    assert service.compute_summary().fairness.max_rank_change == 0

    def leaky(profile, levels):  # type: ignore[no-untyped-def]
        bonus = 3.0 if profile.segment == "graduate" else 0.0
        skills = {k: float(v) + bonus for k, v in levels.items()}
        return MatchProfile(skills=skills, interests=frozenset(profile.interests))

    monkeypatch.setattr(matching_repository, "profile_to_match", leaky)
    assert service.compute_summary().fairness.max_rank_change > 0


def test_no_cost_or_budget_metric_is_shipped_or_served(client: TestClient) -> None:
    body = client.get(URL).json()

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {key for item in value.values() for key in keys(item)}
        if isinstance(value, list):
            return {key for item in value for key in keys(item)}
        return set()

    assert not any("cost" in key or "budget" in key for key in keys(body))
    assert not (service.SEED_DIR / "impact" / "measured_costs.json").exists()


def test_catalogue_totals_follow_authoritative_rows(client: TestClient) -> None:
    coverage = client.get(URL).json()["catalogue"]
    courses = pathway_data.catalogue()
    free = [course for course in courses if course.cost_myr == 0]
    assert coverage["course_count"] == len(courses)
    assert coverage["free_course_count"] == len(free)
    assert coverage["free_course_share"] == round(len(free) / len(courses), 4)
    assert coverage["free_hours"] == round(sum(course.hours for course in free), 1)
    assert coverage["role_count"] == len(service.refdata.rows("taxonomy", "roles"))
    assert coverage["target_role_count"] == len(pathway_data.target_role_ids())
    assert sum(bucket["count"] for bucket in coverage["by_language"]) == len(courses)
    assert coverage["as_of"] == max(course.verified_at for course in courses).isoformat()


def test_public_evidence_items_are_complete_and_sourced(client: TestClient) -> None:
    items = client.get(URL).json()["public_evidence"]
    assert 4 <= len(items) <= 6
    for e in items:
        assert e["url"].startswith("https://") and e["publisher"] and e["quote"].strip()
        assert date.fromisoformat(e["retrieved_at"])
        assert len(e["quote"].split()) <= 15
        EvidenceItem.model_validate(e)  # numeric support/value/publication-date gate
    ids = [e["id"] for e in items]
    assert len(ids) == len(set(ids))
    assert {s["url"] for s in client.get(URL).json()["meta"]["sources"]} >= {
        e["url"] for e in items
    }


def test_unrelated_figure_is_rejected_even_with_a_nonempty_claim() -> None:
    record = service.public_evidence()[0].model_dump()
    record.update(figure="123,456", value=123456)
    with pytest.raises(ValueError, match="quotation or claim"):
        EvidenceItem.model_validate(record)


def test_api_image_packages_the_synthetic_profile_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = SERVICE_FILE.parents[5]
    dockerfile = (root / "src/docker/api.Dockerfile").read_text()
    assert "COPY docs/demo-cvs/profiles.json docs/demo-cvs/profiles.json" in dockerfile
    packaged = tmp_path / "docs/demo-cvs/profiles.json"
    packaged.parent.mkdir(parents=True)
    packaged.write_text((root / "docs/demo-cvs/profiles.json").read_text())
    monkeypatch.setattr(service, "DEMO_PROFILES", packaged)
    assert len(service.load_personas()) == len(json.loads(packaged.read_text()))
    assert service.load_personas(), "packaged impact evidence must not lose all personas"


def test_service_never_reads_the_clock() -> None:
    for path in (SERVICE_FILE, SERVICE_FILE.with_name("router.py")):
        text = path.read_text(encoding="utf-8")
        assert "today(" not in text and "now(" not in text


# Numeric literals allowed in the service: structural (indices, rounding digits, shares), the
# documented definition parameters (30-day window, top 5, 100/500 MYR band edges, 1,000 request
# unit). Any other number would be a typed-in metric.
ALLOWED_LITERALS = {0, 1, 2, 4, 5, 30, 100, 500, 503}


def test_no_numeric_constant_can_become_a_displayed_metric() -> None:
    tree = ast.parse(SERVICE_FILE.read_text(encoding="utf-8"))
    found = {
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, int | float)
        and not isinstance(n.value, bool)
    }
    assert found <= ALLOWED_LITERALS, f"unexpected numeric literals: {found - ALLOWED_LITERALS}"
    # Contract constructors must not be given literal numbers as keyword values.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int | float):
                    assert kw.arg == "status_code" or kw.value.value in (0, 1), kw.arg
