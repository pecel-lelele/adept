"""Catalogue omissions remain reviewable wording, never scored or persisted skills."""

import pytest
from fastapi.testclient import TestClient

from app.features.preview.router import build_preview
from app.features.profile import cv_parser


@pytest.mark.parametrize("heading", ["Skills", "Kemahiran", "技能"])
def test_mixed_list_preserves_unknown_terms_and_resolves_approved_aliases(heading: str) -> None:
    found, _, unknown = cv_parser.parse_cv_review(f"{heading}: Python, dbt, Rust, rust, QlikSense")
    assert {skill.skill_id for skill in found} == {"python", "data-pipelines"}
    assert unknown == ["Rust", "QlikSense"]


def test_only_explicit_skill_lists_are_used_and_next_section_ends_review() -> None:
    _, _, unknown = cv_parser.parse_cv_review(
        "Demo Person\nWorked with Rust and QlikSense.\nSkills\n- Rust\n- QlikSense\n"
        "Experience\nDemo Company\nEducation\nDemo University"
    )
    assert unknown == ["Rust", "QlikSense"]
    assert cv_parser.parse_cv_review("Worked with Rust and QlikSense.")[2] == []


def test_unknown_review_has_no_contact_markup_negated_or_unbounded_items() -> None:
    text = "Skills: Rust, demo@example.test, https://example.test, <script>alert(1)</script>, "
    text += "No QlikSense, 0123456789, " + "x" * 65
    _, _, unknown = cv_parser.parse_cv_review(text)
    assert unknown == ["Rust"]
    assert (
        len(cv_parser.parse_cv_review("Skills: " + ", ".join(f"Tool{i}" for i in range(100)))[2])
        == 30
    )


def test_partial_known_word_does_not_hide_unfamiliar_part() -> None:
    found, _, unknown = cv_parser.parse_cv_review("Skills: Rust with SQL")
    assert {skill.skill_id for skill in found} == {"sql"}
    assert unknown == ["Rust with SQL"]


def test_review_respects_text_truncation() -> None:
    found, truncated, unknown = cv_parser.parse_cv_review("x" * 200_000 + "\nSkills: Rust")
    assert truncated is True
    assert found == unknown == []


def test_unknown_only_preview_has_no_fabricated_role_or_score() -> None:
    preview = build_preview("demo.txt", b"Skills: Rust, QlikSense", "text/plain", "moderate")
    assert preview.skills == []
    assert preview.unmatched_terms == ["Rust", "QlikSense"]
    assert preview.top_role is None
    assert preview.other_role_count == 0


def test_upload_returns_review_terms_without_changing_profile(client: TestClient) -> None:
    before = client.get("/api/v1/profile/me").json()
    response = client.post(
        "/api/v1/profile/cv",
        files={"file": ("demo.txt", b"Skills: Python, Rust", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["unmatched_terms"] == ["Rust"]
    assert client.get("/api/v1/profile/me").json() == before
