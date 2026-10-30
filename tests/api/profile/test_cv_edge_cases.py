"""CV edge cases: Word files, hostile archives, locked PDFs, level cues and other languages.

All CV text here is invented for the test; no real person's CV is used.
"""

from __future__ import annotations

import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import AppError
from app.features.profile import cv_parser
from app.features.profile.cv_parser import DOCX_MIME, extract_skills, extract_text

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(*paragraphs: str, extra: dict[str, bytes] | None = None) -> bytes:
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = f'<?xml version="1.0"?><w:document xmlns:w="{_W}"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", xml)
        for name, data in (extra or {}).items():
            zf.writestr(name, data)
    return buf.getvalue()


def _levels(text: str) -> dict[str, int]:
    return {s.skill_id: s.level for s in extract_skills(cv_parser.clean_text(text))}


def test_docx_text_is_extracted() -> None:
    text = extract_text(_docx("Skills", "SQL and Python programming"), DOCX_MIME)
    assert "SQL and Python programming" in text


def test_docx_without_document_part_is_rejected() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("hello.txt", "not a word file")
    with pytest.raises(AppError) as exc:
        extract_text(buf.getvalue(), DOCX_MIME)
    assert exc.value.code == "docx_unreadable"


def test_docx_that_inflates_too_far_is_refused_before_reading() -> None:
    bomb = _docx("x", extra={"word/header1.xml": b"<a/>" + b" " * 10})
    with patch.object(cv_parser, "MAX_DOCX_XML_BYTES", 50):
        with pytest.raises(AppError) as exc:
            extract_text(bomb, DOCX_MIME)
    assert exc.value.status_code == 413


def test_not_a_zip_is_unreadable() -> None:
    with pytest.raises(AppError) as exc:
        extract_text(b"plain words, not a zip", DOCX_MIME)
    assert exc.value.code == "docx_unreadable"


def test_binary_sent_as_text_is_not_scanned() -> None:
    with pytest.raises(AppError) as exc:
        extract_text(b"%PDF-1.7 binary", "text/plain")
    assert exc.value.code == "wrong_file_type"


def test_password_protected_pdf_says_so() -> None:
    doc = MagicMock(needs_pass=True)
    fitz = MagicMock()
    fitz.open.return_value = doc
    with patch.object(cv_parser, "_HAS_FITZ", True), patch.object(cv_parser, "fitz", fitz):
        with pytest.raises(AppError) as exc:
            extract_text(b"%PDF-1.7 locked", "application/pdf")
    assert exc.value.code == "pdf_encrypted"
    doc.close.assert_called_once()


def test_only_the_first_pages_of_a_long_pdf_are_read() -> None:
    page = MagicMock()
    page.get_text.return_value = "SQL"
    doc = MagicMock(needs_pass=False)
    doc.__iter__ = MagicMock(return_value=iter([page] * 500))
    fitz = MagicMock()
    fitz.open.return_value = doc
    with patch.object(cv_parser, "_HAS_FITZ", True), patch.object(cv_parser, "fitz", fitz):
        extract_text(b"%PDF-1.7 long", "application/pdf")
    assert page.get_text.call_count == cv_parser.MAX_PDF_PAGES


@pytest.mark.parametrize(
    ("page_texts", "truncated", "pages_read"),
    [
        pytest.param(["a" * 10, "SQL"], True, 2, id="exact-limit-then-text"),
        pytest.param(["aaaa", "bbbbb", "SQL"], True, 3, id="joined-limit-then-text"),
        pytest.param(["a" * 9, "SQL"], True, 2, id="separator-at-limit"),
        pytest.param(["a" * 10], False, 1, id="exact-limit-at-end"),
        pytest.param(["aaaa", "bbbbb"], False, 2, id="joined-limit-at-end"),
        pytest.param(["a" * 11, "SQL"], True, 1, id="stop-after-overflow"),
    ],
)
def test_pdf_text_budget_preserves_truncation_detection(
    page_texts: list[str], truncated: bool, pages_read: int
) -> None:
    pages = [MagicMock() for _ in page_texts]
    for page, text in zip(pages, page_texts, strict=True):
        page.get_text.return_value = text
    doc = MagicMock(needs_pass=False)
    doc.__len__.return_value = len(pages)
    doc.__iter__.return_value = iter(pages)
    fitz = MagicMock()
    fitz.open.return_value = doc
    with (
        patch.object(cv_parser, "_HAS_FITZ", True),
        patch.object(cv_parser, "fitz", fitz),
        patch.object(cv_parser, "MAX_TEXT_CHARS", 10),
    ):
        raw = extract_text(b"%PDF-1.7 synthetic", "application/pdf")
        retained, was_truncated = cv_parser._truncate_text(raw)

    assert raw == "\n".join(page_texts)[:11]
    assert retained == "\n".join(page_texts)[:10]
    assert was_truncated is truncated
    assert sum(page.get_text.call_count for page in pages) == pages_read
    doc.close.assert_called_once()


def test_level_words_match_whole_words_only() -> None:
    # "leadership" used to read as "lead" (expert); now it is no level cue at all.
    assert _levels("Python programming, leadership of a small team")["python"] == 2


def test_years_of_experience_set_the_level() -> None:
    assert _levels("6 years of SQL reporting")["sql"] == 4
    assert _levels("SQL - 2 tahun")["sql"] == 2


def test_negated_skills_are_skipped() -> None:
    found = _levels("No experience with Python. Strong SQL.")
    assert "python" not in found
    assert found["sql"] == 4


def test_cjk_aliases_match_inside_a_sentence() -> None:
    with patch.object(
        cv_parser,
        "_load_taxonomy",
        return_value={
            "project-management": cv_parser.TaxonomySkill(
                "project-management", "Project management", "project management", ("项目管理",)
            )
        },
    ):
        cv_parser._build_alias_index.cache_clear()
        try:
            found = extract_skills("我负责项目管理和团队协调")
        finally:
            cv_parser._build_alias_index.cache_clear()
    assert [s.skill_id for s in found] == ["project-management"]


def test_word_upload_is_accepted_by_the_api(client) -> None:  # noqa: ANN001
    resp = client.post(
        "/api/v1/profile/cv",
        files={"file": ("cv.docx", io.BytesIO(_docx("Advanced SQL")), DOCX_MIME)},
    )
    assert resp.status_code == 200, resp.text
    assert any(s["skill_id"] == "sql" for s in resp.json()["skills"])


def test_old_word_format_gets_a_helpful_415(client) -> None:  # noqa: ANN001
    resp = client.post(
        "/api/v1/profile/cv",
        files={"file": ("cv.doc", io.BytesIO(b"\xd0\xcf\x11\xe0"), "application/msword")},
    )
    assert resp.status_code == 415
    assert ".docx" in resp.json()["error"]["message"]


def test_a_denial_on_one_line_does_not_hide_the_next_line() -> None:
    assert _levels("No formal training\nSQL - 5 years experience")["sql"] == 4


def test_years_and_cue_words_stay_with_their_own_skill() -> None:
    found = _levels("SQL; 8 years of Python experience")
    assert found["sql"] == 2
    assert found["python"] == 5
    mixed = _levels("Advanced Excel, basic SQL")
    assert mixed["excel"] == 4
    assert mixed["sql"] == 2
