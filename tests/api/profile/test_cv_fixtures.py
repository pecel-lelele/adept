"""Synthetic CV fixtures: parser coverage and a real endpoint upload (Prompt 9 / item 9).

The files under `fixtures/cvs/` are generated, never hand-written — see
`src/scripts/generate_mock_cvs.py`. Expected skill IDs come from the same seed CSVs
the generator reads, through the shared persona loader, so this test carries no copy
of persona data (the M2-008 rule for the benchmark applies here too).

PDF tests skip with an install hint when PyMuPDF is absent: the parser raises
`PdfSupportUnavailable` rather than decoding PDF bytes as text, so there is nothing
to assert about content in that case.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# pyrefly: ignore[missing-import]
from app.features.matching.personas import load_persona_profile
from app.features.profile import cv_parser
from app.features.profile.cv_parser import extract_text, parse_cv

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cvs"
PERSONAS = ("aisyah", "weijie", "ravi")
REGEN = "uv run --no-project python src/scripts/generate_mock_cvs.py"

EXPECTED_FIXTURES = {
    "cv_aisyah.pdf",
    "cv_weijie.pdf",
    "cv_ravi.pdf",
    "cv_data_entry.pdf",
    "cv_python_programming.pdf",
    "cv_java_javascript.pdf",
    "cv_scanned.pdf",
    "cv_long.txt",
}

needs_pdf = pytest.mark.skipif(
    not cv_parser._HAS_FITZ,
    reason=(
        "PyMuPDF is not installed, so the PDF fixtures cannot be read. "
        "Install it with: uv pip install --python .venv 'pymupdf>=1.24.0,<2'"
    ),
)
needs_fixtures = pytest.mark.skipif(
    not FIXTURES.is_dir(), reason=f"CV fixtures are missing. Regenerate: {REGEN}"
)


def _fixture(name: str) -> Path:
    path = FIXTURES / name
    if not path.exists():
        pytest.skip(f"{name} is missing. Regenerate: {REGEN}")
    return path


def _persona_skill_ids(uid: str) -> set[str]:
    persona = load_persona_profile(uid)
    assert persona is not None, f"{uid} is not in src/data/seed/personas"
    return set(persona.skills)


def _upload(name: str, content_type: str = "application/pdf") -> dict[str, tuple[str, bytes, str]]:
    """Multipart body for TestClient, declaring the MIME type the router expects."""
    return {"file": (name, _fixture(name).read_bytes(), content_type)}


# ---------------------------------------------------------------------------
# The fixture set itself
# ---------------------------------------------------------------------------


@needs_fixtures
def test_every_documented_fixture_exists() -> None:
    """Three persona CVs plus the five edge fixtures, all present on disk."""
    present = {p.name for p in FIXTURES.iterdir()}
    assert EXPECTED_FIXTURES <= present, f"missing {sorted(EXPECTED_FIXTURES - present)}: {REGEN}"


# ---------------------------------------------------------------------------
# One CV per synthetic persona: same name, segment and skills as the seed files
# ---------------------------------------------------------------------------


@needs_fixtures
@needs_pdf
@pytest.mark.parametrize("uid", PERSONAS)
def test_persona_cv_extracts_the_seeded_skills(uid: str) -> None:
    """Parsing a persona's CV returns exactly the skill IDs seeded for that persona."""
    parsed, truncated = parse_cv(_fixture(f"cv_{uid}.pdf").read_bytes(), "application/pdf")
    ids = {s.skill_id for s in parsed}

    assert ids == _persona_skill_ids(uid), f"{uid}: parsed {sorted(ids)}"
    assert truncated is False
    assert ids, f"{uid} must expose at least one skill for the demo"


@needs_fixtures
@needs_pdf
def test_persona_cv_email_is_fake_and_stripped_by_cleaning() -> None:
    """Synthetic example.com address in the file; gone after PII cleaning."""
    text = extract_text(_fixture("cv_aisyah.pdf").read_bytes(), "application/pdf")
    assert "aisyah@example.com" in text, "fixture email must be on example.com"
    assert "@" not in cv_parser._clean_text(text), "PII cleaning must strip the email"


# ---------------------------------------------------------------------------
# Edge fixtures
# ---------------------------------------------------------------------------


@needs_fixtures
@needs_pdf
def test_data_entry_does_not_match_data_skills() -> None:
    """The phrase "data entry" is not a taxonomy alias: nothing may be invented."""
    parsed, _ = parse_cv(_fixture("cv_data_entry.pdf").read_bytes(), "application/pdf")
    ids = {s.skill_id for s in parsed}
    assert ids == set(), f"cv_data_entry.pdf matched {sorted(ids)}"
    assert "manual-data-entry" not in ids
    assert "data-visualisation" not in ids


@needs_fixtures
@needs_pdf
def test_python_programming_appears_once() -> None:
    """One mention of the label => one entry, one non-overlapping hit, confidence 0.30."""
    parsed, _ = parse_cv(_fixture("cv_python_programming.pdf").read_bytes(), "application/pdf")
    python = [s for s in parsed if s.skill_id == "python"]

    assert len(python) == 1, f"expected one python entry, got {len(python)}"
    assert python[0].confidence == pytest.approx(cv_parser.CONFIDENCE_PER_HIT)
    assert {s.skill_id for s in parsed} == {"python"}


@needs_fixtures
@needs_pdf
def test_java_and_javascript_invent_no_skills() -> None:
    """Neither Java nor JavaScript is in the taxonomy, so the result must be empty.

    Also proves the word-boundary rule: "java" must not match inside "JavaScript".
    """
    parsed, _ = parse_cv(_fixture("cv_java_javascript.pdf").read_bytes(), "application/pdf")
    ids = {s.skill_id for s in parsed}
    assert ids == set(), f"cv_java_javascript.pdf matched {sorted(ids)}"
    assert not any("java" in sid for sid in ids)


@needs_fixtures
@needs_pdf
def test_scanned_pdf_has_no_selectable_text() -> None:
    """An image-only PDF must raise PdfNoText (422), never fall back to raw bytes."""
    from app.core.errors import PdfNoText

    with pytest.raises(PdfNoText) as exc_info:
        extract_text(_fixture("cv_scanned.pdf").read_bytes(), "application/pdf")
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "pdf_no_text"


@needs_fixtures
def test_long_text_fixture_shape() -> None:
    """100,000 characters and no '@' anywhere."""
    raw = _fixture("cv_long.txt").read_bytes()
    assert len(raw) == 100_000, f"cv_long.txt is {len(raw)} bytes"
    assert raw.count(b"@") == 0


@needs_fixtures
def test_long_text_parses_fast_and_matches_nothing() -> None:
    """ReDoS guard on a real file: cleaning and scanning 100k chars stays under 5 s."""
    start = time.monotonic()
    parsed, truncated = parse_cv(_fixture("cv_long.txt").read_bytes(), "text/plain")
    elapsed = time.monotonic() - start

    assert elapsed < 5.0, f"parse took {elapsed:.2f}s"
    assert parsed == []
    assert truncated is False, "100,000 chars is below MAX_TEXT_CHARS"


# ---------------------------------------------------------------------------
# The endpoint itself, with no UI in the loop
# ---------------------------------------------------------------------------


@needs_fixtures
@needs_pdf
def test_cv_endpoint_accepts_generated_pdf(client: TestClient) -> None:
    """POST /profile/cv with a real generated PDF returns the persona's skills."""
    resp = client.post(
        "/api/v1/profile/cv",
        files=_upload("cv_aisyah.pdf"),
        headers={"X-Demo-User": "aisyah"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {s["skill_id"] for s in body["skills"]} == _persona_skill_ids("aisyah")
    assert body["truncated"] is False
    taxonomy = cv_parser._load_taxonomy()
    assert all(s["skill_id"] in taxonomy for s in body["skills"]), "invented skill id"


@needs_fixtures
@needs_pdf
def test_cv_endpoint_rejects_scanned_pdf(client: TestClient) -> None:
    """A scanned-only upload is a clean 422 with the pdf_no_text code."""
    resp = client.post(
        "/api/v1/profile/cv",
        files=_upload("cv_scanned.pdf"),
        headers={"X-Demo-User": "aisyah"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "pdf_no_text"


@needs_fixtures
def test_cv_endpoint_accepts_long_text_fixture(client: TestClient) -> None:
    """100k chars is well under the 5 MB cap: 200, no skills, truncated=False."""
    resp = client.post(
        "/api/v1/profile/cv",
        files={"file": ("cv_long.txt", _fixture("cv_long.txt").read_bytes(), "text/plain")},
        headers={"X-Demo-User": "weijie"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["skills"] == []
    assert resp.json()["truncated"] is False
