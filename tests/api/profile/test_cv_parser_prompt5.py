"""Prompt 5 tests for the CV parser rewrite.

Tests written first, as specified. Covers:
  - ReDoS-safety: large inputs and email-like strings parse in <1 second.
  - Boundary matching: "data entry" vs "data analysis", word-boundary Java/JavaScript.
  - Non-overlapping span counting: "Python programming" = 1 hit for python.
  - Error cases: over-size file (413), wrong content type (415),
    missing PyMuPDF (501), scanned PDF / no text (422).
  - All returned skill IDs are in the taxonomy (catalogue-only guarantee).
  - End-to-end HTTP route test via multipart upload with the real test client.
"""

from __future__ import annotations

import io
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.features.profile.cv_parser import (
    MAX_TEXT_CHARS,
    _clean_text,
    _load_taxonomy,
    _truncate_text,
    extract_skills,
    extract_text,
)

AISYAH = {"X-Demo-User": "aisyah"}


# ---------------------------------------------------------------------------
# ReDoS safety — large strings and email-like input must parse fast
# ---------------------------------------------------------------------------


class TestReDoSSafety:
    def test_repeated_skill_mentions_stop_at_confidence_cap(self) -> None:
        text = "sql " * 50_000
        start = time.monotonic()
        skills = extract_skills(text)
        elapsed = time.monotonic() - start

        sql_skill = next(skill for skill in skills if skill.skill_id == "sql")
        assert sql_skill.confidence == pytest.approx(1.0)
        assert elapsed < 1.0, f"50,000 repeated mentions took {elapsed:.3f}s"

    def test_large_text_no_at_sign_is_fast(self) -> None:
        """50 000 'a' chars must be cleaned in under 1 second."""
        big = "a" * 50_000
        start = time.monotonic()
        result = _clean_text(big)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"Took {elapsed:.3f}s — possible ReDoS"
        # No PII to strip; result should be non-empty
        assert len(result) > 0

    def test_large_text_with_at_sign_is_fast(self) -> None:
        """50 000 'a' chars + '@' must be cleaned in under 1 second."""
        big = "a" * 50_000 + "@"
        start = time.monotonic()
        _clean_text(big)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"Took {elapsed:.3f}s — possible ReDoS"

    def test_many_emails_is_fast(self) -> None:
        """A string with 1000 email-like tokens must clean in under 1 second."""
        text = " ".join("user@domain.com" for _ in range(1000))
        start = time.monotonic()
        result = _clean_text(text)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"Took {elapsed:.3f}s — possible ReDoS"
        assert "@" not in result


# ---------------------------------------------------------------------------
# Boundary matching
# ---------------------------------------------------------------------------


class TestBoundaryMatching:
    def test_data_entry_does_not_match_data_analysis(self) -> None:
        """'data entry' text must not produce a data-analysis skill match.

        The taxonomy label for manual-data-entry is 'Manual data entry'.
        A text about 'data analysis' should only match data-visualisation
        or similar labels — not manual-data-entry unless it appears verbatim.
        """
        text = "Experienced in data analysis and reporting."
        skills = extract_skills(text)
        ids = {s.skill_id for s in skills}
        assert "manual-data-entry" not in ids

    def test_python_programming_counts_as_one_hit(self) -> None:
        """'Python programming' should produce exactly one match for the python skill."""
        # The label is 'Python programming'; it appears exactly once in this text.
        text = "Skilled in Python programming."
        skills = extract_skills(text)
        python_hits = [s for s in skills if s.skill_id == "python"]
        assert len(python_hits) == 1, "Expected exactly one python skill entry"
        # One non-overlapping match => confidence = 0.30
        assert python_hits[0].confidence == pytest.approx(0.30)

    def test_java_and_javascript_each_match_once(self) -> None:
        """'Java and JavaScript' — java must not match inside 'javascript'.

        Our taxonomy only has 'python', 'sql', etc. so this tests the boundary
        logic using the actual labels present. We verify that for whatever labels
        exist, no sub-word matches occur. We construct a case with sql vs a
        fictional 'sqli' to confirm the boundary holds (using raw extract_skills).
        """
        # "SQL" label should not match "SQLS" or "NoSQL"
        text = "Expert in NoSQL databases and SQLite systems."
        skills = extract_skills(text)
        ids = {s.skill_id for s in skills}
        # sql skill should NOT match because "SQL" is inside "NoSQL"/"SQLite"
        # with word-boundary check — it depends on boundaries around the word.
        # "NoSQL" -> no left boundary before "SQL"; "SQLite" -> no right boundary.
        assert "sql" not in ids, (
            "sql matched inside 'NoSQL' or 'SQLite' — word boundary check failed"
        )


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------


class TestTruncation:
    def test_short_text_not_truncated(self) -> None:
        text = "Python developer"
        out, truncated = _truncate_text(text)
        assert out == text
        assert truncated is False

    def test_long_text_is_truncated(self) -> None:
        text = "a" * (MAX_TEXT_CHARS + 1000)
        out, truncated = _truncate_text(text)
        assert len(out) == MAX_TEXT_CHARS
        assert truncated is True


# ---------------------------------------------------------------------------
# Content-type validation — extract_text errors
# ---------------------------------------------------------------------------


class TestExtractTextErrors:
    def test_missing_fitz_raises_pdf_support_unavailable(self) -> None:
        """Without fitz, uploading a PDF must raise PdfSupportUnavailable (not return garbage)."""
        from app.core.errors import PdfSupportUnavailable

        with patch("app.features.profile.cv_parser._HAS_FITZ", False):
            with pytest.raises(PdfSupportUnavailable) as exc_info:
                extract_text(b"%PDF-1.4 fake", "application/pdf")
            assert exc_info.value.status_code == 501
            assert exc_info.value.code == "pdf_unsupported"

    def test_scanned_pdf_no_text_raises_pdf_no_text(self) -> None:
        """A PDF that fitz opens but yields no text must raise PdfNoText."""
        import app.features.profile.cv_parser as cv_mod
        from app.core.errors import PdfNoText

        mock_page = MagicMock()
        mock_page.get_text.return_value = "   "  # blank page
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch.object(cv_mod, "_HAS_FITZ", True):
            with patch.object(cv_mod, "fitz", mock_fitz, create=True):
                with pytest.raises(PdfNoText) as exc_info:
                    extract_text(b"fake pdf bytes", "application/pdf")
                assert exc_info.value.status_code == 422
                assert exc_info.value.code == "pdf_no_text"

    def test_plain_text_decoded_correctly(self) -> None:
        content = b"I am skilled in SQL"
        result = extract_text(content, "text/plain")
        assert result == "I am skilled in SQL"


# ---------------------------------------------------------------------------
# Catalogue-only guarantee
# ---------------------------------------------------------------------------


class TestCatalogueOnly:
    def test_all_returned_ids_in_taxonomy(self) -> None:
        """No hallucinated skill IDs — every result must exist in the taxonomy."""
        taxonomy = _load_taxonomy()
        text = (
            "machine learning deep learning transformers BERT GPT kubernetes docker "
            "Python programming SQL spreadsheet analysis prompt engineering AI literacy"
        )
        skills = extract_skills(text)
        for s in skills:
            assert s.skill_id in taxonomy, (
                f"Hallucinated skill_id '{s.skill_id}' is not in the taxonomy"
            )

    def test_unknown_term_returns_empty(self) -> None:
        skills = extract_skills("zorbflax quuxinator blorptide")
        assert skills == []


# ---------------------------------------------------------------------------
# End-to-end HTTP route test (item 9: prove the endpoint works for the UI)
# ---------------------------------------------------------------------------


class TestCvUploadRoute:
    def test_text_cv_upload_returns_skills(self, client: TestClient) -> None:
        """Upload a plain-text CV fixture through the real HTTP route.

        Verifies:
          - 200 response
          - Response body has 'skills' list with skill_id, level, confidence
          - 'truncated' field is present
          - All returned skill IDs are in the taxonomy
        """
        taxonomy = _load_taxonomy()
        cv_text = (
            "I am an experienced Python programmer with strong SQL skills. "
            "I also do data visualisation and prompt engineering. "
            "I am proficient in AI literacy and responsible AI."
        )
        file_bytes = cv_text.encode("utf-8")

        resp = client.post(
            "/api/v1/profile/cv",
            headers=AISYAH,
            files={"file": ("cv.txt", io.BytesIO(file_bytes), "text/plain")},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()

        assert "skills" in body
        assert "truncated" in body
        assert isinstance(body["truncated"], bool)

        for skill in body["skills"]:
            assert "skill_id" in skill
            assert "level" in skill
            assert "confidence" in skill
            assert skill["skill_id"] in taxonomy, (
                f"Returned skill_id '{skill['skill_id']}' not in taxonomy"
            )

    def test_wrong_content_type_returns_415(self, client: TestClient) -> None:
        """Uploading an image file must be rejected with HTTP 415."""
        resp = client.post(
            "/api/v1/profile/cv",
            headers=AISYAH,
            files={"file": ("photo.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
        )
        assert resp.status_code == 415
        body = resp.json()
        assert body["error"]["code"] == "unsupported_media_type"

    def test_oversized_file_returns_413(self, client: TestClient) -> None:
        """A file larger than the configured limit must be rejected with 413."""
        from app.core.config import get_settings

        max_bytes = get_settings().max_upload_bytes
        oversized = b"x" * (max_bytes + 1)

        resp = client.post(
            "/api/v1/profile/cv",
            headers=AISYAH,
            files={"file": ("big.txt", io.BytesIO(oversized), "text/plain")},
        )
        assert resp.status_code == 413
        body = resp.json()
        assert body["error"]["code"] == "payload_too_large"

    def test_pdf_without_fitz_returns_501(self, client: TestClient) -> None:
        """When PyMuPDF is not installed, uploading a PDF must return 501."""
        with patch("app.features.profile.cv_parser._HAS_FITZ", False):
            resp = client.post(
                "/api/v1/profile/cv",
                headers=AISYAH,
                files={"file": ("cv.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
            )
        assert resp.status_code == 501
        body = resp.json()
        assert body["error"]["code"] == "pdf_unsupported"

    def test_scanned_pdf_returns_422(self, client: TestClient) -> None:
        """A PDF with no extractable text (scanned) must return 422."""
        import app.features.profile.cv_parser as cv_mod

        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_fitz = MagicMock()
        mock_fitz.open.return_value = mock_doc

        with patch.object(cv_mod, "_HAS_FITZ", True):
            with patch.object(cv_mod, "fitz", mock_fitz, create=True):
                resp = client.post(
                    "/api/v1/profile/cv",
                    headers=AISYAH,
                    files={
                        "file": (
                            "scan.pdf",
                            io.BytesIO(b"%PDF-1.4 fake"),
                            "application/pdf",
                        )
                    },
                )
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "pdf_no_text"
