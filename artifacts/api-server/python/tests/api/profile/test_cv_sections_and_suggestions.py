"""Skills sections end at any other heading, wrapped lists stay whole, and embedding-based
suggestions are proposals that never replace exact catalogue matching."""

from __future__ import annotations

import math
import random

import pytest

from app.core import embeddings
from app.features.profile import cv_parser, skill_match

CV = """SOFIA TAN
Process Automation Analyst
sofia.tan@example.test
PROFESSIONAL SUMMARY
Process automation analyst with four years of experience.
CORE SKILLS
Process mapping; robotic process automation (RPA); Python; SQL; workflow validation; exception
handling.
PROFESSIONAL EXPERIENCE
Process Automation Analyst
2022 – Present
Rimba Demo Workflow Studio
Fictional employer, Malaysia
• Mapped invoice intake and approval workflows with colleagues, identifying decision points
SELECTED PROJECT
Created a supervised RPA demonstration.
"""


def test_skills_section_stops_at_any_heading_and_rejoins_wrapped_entries() -> None:
    entries = cv_parser.skills_section_entries(CV)
    assert entries == [
        "Process mapping",
        "robotic process automation (RPA)",
        "Python",
        "SQL",
        "workflow validation",
        "exception handling",
    ]
    assert cv_parser.unmatched_skill_terms(CV) == ["workflow validation", "exception handling"]


@pytest.mark.parametrize(
    "noise", ["Rimba Demo Workflow Studio", "Fictional employer", "Malaysia", "2022", "SOFIA TAN"]
)
def test_employers_titles_dates_and_names_are_never_review_terms(noise: str) -> None:
    assert noise not in cv_parser.unmatched_skill_terms(CV)


def test_hyphenated_line_breaks_and_sub_labels() -> None:
    text = "Skills\nTools: Excel, Power BI, field val-\nidation\nLanguages\nEnglish"
    assert cv_parser.skills_section_entries(text) == ["Excel", "Power BI", "field validation"]


def test_inline_heading_and_one_entry_per_line() -> None:
    text = "Skills: Python, SQL\nKemahiran\n- Rust\n- QlikSense\nPendidikan\nUniversiti Demo"
    assert cv_parser.skills_section_entries(text) == ["Python", "SQL", "Rust", "QlikSense"]


# --- embedding suggestions (fake vectors: no network in tests) -------------------------------


def _vec(seed: str) -> list[float]:
    rng = random.Random(seed)  # independent pseudo-random directions per text
    raw = [rng.gauss(0, 1) for _ in range(embeddings.DIMS)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


def test_decide_needs_similarity_and_a_clear_lead() -> None:
    labels = {"a": "A", "b": "B"}
    assert skill_match.decide("t", [("a", 0.86), ("b", 0.80)], labels, set()).skill_id == "a"  # type: ignore[union-attr]
    assert skill_match.decide("t", [("a", 0.79), ("b", 0.70)], labels, set()) is None  # too far
    assert skill_match.decide("t", [("a", 0.85), ("b", 0.845)], labels, set()) is None  # ambiguous
    assert (
        skill_match.decide("t", [("a", 0.86), ("b", 0.80)], labels, {"a"}) is None
    )  # already found


def test_suggestions_are_off_without_a_provider() -> None:
    assert not embeddings.enabled()  # the test suite never calls a real API
    assert skill_match.suggest(["workflow validation"]) == []


def test_suggest_maps_a_term_to_its_nearest_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    texts = skill_match.catalogue_texts()
    target = "data-visualisation"

    def fake_embed(items: list[str], task: str = "", patient: bool = False) -> list[list[float]]:
        # "Tableau" points at the data visualisation entry; everything else is unrelated.
        return [_vec(texts[target]) if t == "Tableau" else _vec(t) for t in items]

    monkeypatch.setattr(embeddings, "enabled", lambda: True)
    monkeypatch.setattr(embeddings, "embed", fake_embed)
    monkeypatch.setattr(skill_match, "_index", {})
    monkeypatch.setattr(skill_match, "_index_model", "")
    skill_match.ensure_index()  # Explicit offline preparation, never part of the CV request.
    found = skill_match.suggest(["Tableau", "Kuala Lumpur"])
    assert [(s.term, s.skill_id) for s in found] == [("Tableau", target)]
    assert found[0].similarity == pytest.approx(1.0, abs=1e-3)


@pytest.mark.parametrize("acronym", ["SQL", "RPA", "AWS"])
def test_skill_acronyms_do_not_end_the_skills_section(acronym: str) -> None:
    text = f"Skills\n{acronym}\nRust\nQlikSense\nWORK EXPERIENCE\nFictional Employer"
    assert cv_parser.skills_section_entries(text) == [acronym, "Rust", "QlikSense"]
    assert {"Rust", "QlikSense"} <= set(cv_parser.unmatched_skill_terms(text))


def test_cv_suggestions_do_not_build_an_empty_index(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embeddings, "enabled", lambda: True)
    monkeypatch.setattr(skill_match, "_index", {})
    monkeypatch.setattr(skill_match, "_index_model", "")
    monkeypatch.setattr(skill_match.refdata, "use_postgres", lambda: False)
    monkeypatch.setattr(embeddings, "embed", lambda *a, **k: pytest.fail("request built an index"))
    assert skill_match.suggest(["Tableau"]) == []


def test_cv_request_does_not_wait_for_an_index_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embeddings, "enabled", lambda: True)
    with skill_match._lock:
        assert skill_match.suggest(["Tableau"]) == []


def test_embedding_failure_falls_back_to_exact_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_: object, **__: object) -> list[list[float]]:
        raise embeddings.EmbeddingsUnavailable("down")

    monkeypatch.setattr(embeddings, "enabled", lambda: True)
    monkeypatch.setattr(embeddings, "embed", boom)
    assert skill_match.suggest(["Tableau"]) == []
