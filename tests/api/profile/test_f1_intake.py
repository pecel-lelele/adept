"""Tests for F1 Profile Intake Pipeline (M2-01, M2-02, M2-03).

Covers:
  - M2-01: CV parsing pipeline (keyword extraction, confidence, level heuristics)
  - M2-02: Intake questionnaire endpoint
  - M2-03: Skill confirmation endpoint — normalisation, validation, deduplication
"""

from __future__ import annotations

import pydantic
import pytest
from fastapi.testclient import TestClient

from app.contracts.profile import CvExtractionResult, Profile
from app.features.profile.cv_parser import (
    clean_text,
    extract_skills,
    extract_text,
    extract_text_from_pdf,
    parse_cv,
)
from app.features.profile.schemas import (
    QuestionnaireIn,
    QuestionnaireResponse,
    SkillConfirmationIn,
    SkillConfirmationResponse,
    SkillEdit,
)
from app.features.profile.service import normalise_level

AISYAH = {"X-Demo-User": "aisyah"}
WEIJIE = {"X-Demo-User": "weijie"}

# ---------------------------------------------------------------------------
# M2-01: cv_parser unit tests
# ---------------------------------------------------------------------------


class TestCleanText:
    def test_strips_urls(self) -> None:
        raw = "Visit https://example.com for more info"
        assert "https://" not in clean_text(raw)

    def test_strips_emails(self) -> None:
        raw = "Contact me at john.doe@email.com"
        assert "@" not in clean_text(raw)

    def test_collapses_whitespace(self) -> None:
        raw = "python   \n\n   sql"
        assert clean_text(raw) == "python sql"

    def test_removes_non_printable(self) -> None:
        raw = "python\x00sql"
        result = clean_text(raw)
        assert "\x00" not in result


class TestExtractText:
    def test_plain_text_roundtrip(self) -> None:
        content = b"I know Python and SQL"
        assert extract_text("cv.txt", content) == "I know Python and SQL"

    def test_pdf_falls_back_to_text_without_fitz(self) -> None:
        """Without fitz installed, PDF bytes are decoded as UTF-8."""
        content = b"Python developer with SQL skills"
        result = extract_text("cv.pdf", content)
        # Should not raise; result may be garbled but non-empty
        assert isinstance(result, str)


class TestExtractSkills:
    def test_extracts_python_from_text(self) -> None:
        text = "I am an intermediate Python developer"
        skills = extract_skills(text)
        ids = [s.skill_id for s in skills]
        assert "python" in ids

    def test_extracts_sql(self) -> None:
        text = "Proficient in SQL and data analysis"
        skills = extract_skills(text)
        ids = [s.skill_id for s in skills]
        assert "sql" in ids

    def test_no_hallucinated_skills(self) -> None:
        """Skills not in taxonomy must never appear."""
        text = "I know machine learning and deep learning and transformers"
        skills = extract_skills(text)
        from app.features.profile.service import _valid_skill_ids

        valid = _valid_skill_ids()
        assert all(s.skill_id in valid for s in skills)

    def test_deduplicates_same_skill(self) -> None:
        """Same skill mentioned twice should appear only once."""
        text = "Python python PYTHON developer"
        skills = extract_skills(text)
        ids = [s.skill_id for s in skills]
        assert ids.count("python") == 1

    def test_confidence_between_zero_and_one(self) -> None:
        text = "Expert Python architect with extensive SQL experience"
        skills = extract_skills(text)
        assert all(0.0 <= s.confidence <= 1.0 for s in skills)

    def test_expert_keyword_raises_level(self) -> None:
        text = "Expert Python architect"
        skills = extract_skills(text)
        py = next((s for s in skills if s.skill_id == "python"), None)
        assert py is not None
        assert py.level >= 4

    def test_basic_keyword_lowers_level(self) -> None:
        text = "Basic awareness of SQL"
        skills = extract_skills(text)
        sq = next((s for s in skills if s.skill_id == "sql"), None)
        assert sq is not None
        assert sq.level <= 2

    def test_empty_text_returns_empty(self) -> None:
        assert extract_skills("") == []


class TestParseCvIntegration:
    def test_parse_text_cv(self) -> None:
        cv_text = (
            b"Aisyah has 3 years of experience with Excel and risk compliance. "
            b"She is learning Python."
        )
        results = parse_cv("aisyah_cv.txt", cv_text)
        ids = [r.skill_id for r in results]
        assert "excel" in ids or "risk-compliance" in ids or "python" in ids

    def test_parse_returns_sorted_by_confidence(self) -> None:
        cv_text = b"Expert Excel user. Basic Python awareness."
        results = parse_cv("cv.txt", cv_text)
        if len(results) > 1:
            confidences = [r.confidence for r in results]
            assert confidences == sorted(confidences, reverse=True)


# ---------------------------------------------------------------------------
# M2-01: service.normalise_level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "level,expected",
    [(1, 0.0), (2, 0.25), (3, 0.5), (4, 0.75), (5, 1.0)],
)
def test_normalise_level(level: int, expected: float) -> None:
    assert normalise_level(level) == expected


# ---------------------------------------------------------------------------
# M2-01: POST /profile/cv — API integration
# ---------------------------------------------------------------------------


class TestCvEndpoint:
    def test_returns_cv_extraction_result_schema(self, client: TestClient) -> None:
        files = {"file": ("synthetic_cv.txt", b"Synthetic CV text", "text/plain")}
        resp = client.post("/api/v1/profile/cv", files=files, headers=AISYAH)
        assert resp.status_code == 200
        body = CvExtractionResult.model_validate(resp.json())
        assert all(0 <= s.confidence <= 1 for s in body.skills)

    def test_real_cv_text_extracts_skills(self, client: TestClient) -> None:
        cv = b"Expert Python developer. Proficient in SQL. AI literacy."
        files = {"file": ("cv.txt", cv, "text/plain")}
        resp = client.post("/api/v1/profile/cv", files=files, headers=AISYAH)
        assert resp.status_code == 200
        body = CvExtractionResult.model_validate(resp.json())
        ids = [s.skill_id for s in body.skills]
        assert "python" in ids or "sql" in ids

    def test_cv_skill_levels_in_valid_range(self, client: TestClient) -> None:
        cv = b"Advanced Python and SQL developer"
        files = {"file": ("cv.txt", cv, "text/plain")}
        resp = client.post("/api/v1/profile/cv", files=files, headers=AISYAH)
        body = CvExtractionResult.model_validate(resp.json())
        assert all(1 <= s.level <= 5 for s in body.skills)

    def test_rejects_oversized_file(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.core.config import get_settings

        monkeypatch.setattr(get_settings(), "max_upload_bytes", 1024)
        files = {"file": ("big.txt", b"x" * 2048, "text/plain")}
        resp = client.post("/api/v1/profile/cv", files=files)
        assert resp.status_code == 413

    def test_accepts_file_at_limit(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.core.config import get_settings

        monkeypatch.setattr(get_settings(), "max_upload_bytes", 1024)
        files = {"file": ("ok.txt", b"x" * 1024, "text/plain")}
        assert client.post("/api/v1/profile/cv", files=files).status_code == 200


# ---------------------------------------------------------------------------
# M2-02: POST /profile/questionnaire
# ---------------------------------------------------------------------------


class TestQuestionnaireEndpoint:
    def _payload(self, **overrides: object) -> dict:
        base: dict = {
            "segment": "graduate",
            "interests": ["data", "AI"],
            "hours_per_week": 10,
            "learning_style": "video",
            "budget_myr": 300.0,
            "hrd_eligible": False,
        }
        base.update(overrides)
        return base

    def test_returns_questionnaire_response(self, client: TestClient) -> None:
        resp = client.post("/api/v1/profile/questionnaire", json=self._payload(), headers=WEIJIE)
        assert resp.status_code == 200
        body = QuestionnaireResponse.model_validate(resp.json())
        assert body.user_id == "weijie"
        assert body.segment == "graduate"
        assert body.learning_style == "video"
        assert body.hours_per_week == 10

    def test_persists_interests_to_profile(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/profile/questionnaire",
            json=self._payload(interests=["software", "analytics"]),
            headers=WEIJIE,
        )
        assert resp.status_code == 200
        profile_resp = client.get("/api/v1/profile/me", headers=WEIJIE)
        profile = Profile.model_validate(profile_resp.json())
        assert "software" in profile.interests or "analytics" in profile.interests

    def test_rejects_invalid_segment(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/profile/questionnaire",
            json=self._payload(segment="invalid_segment"),
            headers=WEIJIE,
        )
        assert resp.status_code == 422

    def test_rejects_hours_per_week_out_of_range(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/profile/questionnaire",
            json=self._payload(hours_per_week=999),
            headers=WEIJIE,
        )
        assert resp.status_code == 422

    def test_rejects_negative_budget(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/profile/questionnaire",
            json=self._payload(budget_myr=-100),
            headers=WEIJIE,
        )
        assert resp.status_code == 422

    def test_filters_demographic_interests(self, client: TestClient) -> None:
        """Demographic interest tags must be silently stripped (M2-12)."""
        resp = client.post(
            "/api/v1/profile/questionnaire",
            json=self._payload(interests=["data", "gender", "AI"]),
            headers=WEIJIE,
        )
        assert resp.status_code == 200
        body = QuestionnaireResponse.model_validate(resp.json())
        assert "gender" not in body.interests

    def test_accepts_all_learning_styles(self, client: TestClient) -> None:
        for style in ("video", "reading", "hands-on", "classroom", "mixed"):
            resp = client.post(
                "/api/v1/profile/questionnaire",
                json=self._payload(learning_style=style),
                headers=AISYAH,
            )
            assert resp.status_code == 200, f"Failed for learning_style={style}"


# ---------------------------------------------------------------------------
# M2-03: PUT /profile/skills/confirm
# ---------------------------------------------------------------------------


class TestSkillConfirmEndpoint:
    def _payload(self, skills: list[dict]) -> dict:
        return {"skills": skills}

    def test_returns_confirmation_response(self, client: TestClient) -> None:
        payload = self._payload([{"skill_id": "python", "level": 3, "source": "confirmed"}])
        resp = client.put("/api/v1/profile/skills/confirm", json=payload, headers=WEIJIE)
        assert resp.status_code == 200
        body = SkillConfirmationResponse.model_validate(resp.json())
        assert body.user_id == "weijie"
        assert len(body.confirmed_skills) == 1
        assert body.confirmed_skills[0].skill_id == "python"

    def test_normalised_level_is_correct(self, client: TestClient) -> None:
        """Level 3 should normalise to 0.5."""
        payload = self._payload([{"skill_id": "python", "level": 3, "source": "confirmed"}])
        resp = client.put("/api/v1/profile/skills/confirm", json=payload, headers=WEIJIE)
        body = SkillConfirmationResponse.model_validate(resp.json())
        normalised = next(s for s in body.normalised_skills if s.skill_id == "python")
        assert normalised.normalised_level == 0.5

    def test_rejects_unknown_skill_id(self, client: TestClient) -> None:
        payload = self._payload(
            [{"skill_id": "nonexistent-skill-xyz", "level": 3, "source": "confirmed"}]
        )
        resp = client.put("/api/v1/profile/skills/confirm", json=payload, headers=WEIJIE)
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "unknown_skill_ids"

    def test_rejects_duplicate_skill_ids(self, client: TestClient) -> None:
        payload = self._payload(
            [
                {"skill_id": "python", "level": 3, "source": "confirmed"},
                {"skill_id": "python", "level": 4, "source": "confirmed"},
            ]
        )
        resp = client.put("/api/v1/profile/skills/confirm", json=payload, headers=WEIJIE)
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "duplicate_skill_ids"

    def test_rejects_level_out_of_range(self, client: TestClient) -> None:
        payload = self._payload([{"skill_id": "python", "level": 9, "source": "confirmed"}])
        resp = client.put("/api/v1/profile/skills/confirm", json=payload, headers=WEIJIE)
        assert resp.status_code == 422

    def test_empty_skill_list_is_accepted(self, client: TestClient) -> None:
        """User may clear all skills."""
        resp = client.put(
            "/api/v1/profile/skills/confirm",
            json=self._payload([]),
            headers=WEIJIE,
        )
        assert resp.status_code == 200

    def test_all_normalised_levels_within_range(self, client: TestClient) -> None:
        payload = self._payload(
            [
                {"skill_id": "python", "level": 1, "source": "confirmed"},
                {"skill_id": "sql", "level": 5, "source": "confirmed"},
                {"skill_id": "excel", "level": 3, "source": "confirmed"},
            ]
        )
        resp = client.put("/api/v1/profile/skills/confirm", json=payload, headers=AISYAH)
        body = SkillConfirmationResponse.model_validate(resp.json())
        assert all(0.0 <= s.normalised_level <= 1.0 for s in body.normalised_skills)

    def test_skill_labels_populated_in_response(self, client: TestClient) -> None:
        payload = self._payload([{"skill_id": "excel", "level": 4, "source": "confirmed"}])
        resp = client.put("/api/v1/profile/skills/confirm", json=payload, headers=AISYAH)
        body = SkillConfirmationResponse.model_validate(resp.json())
        skill = next(s for s in body.normalised_skills if s.skill_id == "excel")
        assert skill.label != ""  # label should be populated from taxonomy


# ---------------------------------------------------------------------------
# Edge Cases: Invalid PDF uploads, malformed text, and corruption tolerance
# ---------------------------------------------------------------------------


class TestCvParserMalformedAndCorruptedInputs:
    def test_corrupted_pdf_stream_falls_back_without_error(self) -> None:
        """Corrupted PDF binary should not throw unhandled exceptions."""
        corrupted_bytes = b"%PDF-1.4\ncorrupted stream \xff\xfe\x00\x01\x80\x99 garbage binary"
        extracted = extract_text_from_pdf(corrupted_bytes)
        assert isinstance(extracted, str)
        # parse_cv should also run safely
        result = parse_cv("corrupted.pdf", corrupted_bytes)
        assert isinstance(result, list)

    def test_truncated_pdf_header(self) -> None:
        """Truncated PDF header should not crash the parser."""
        truncated = b"%PDF-"
        result = parse_cv("truncated.pdf", truncated)
        assert isinstance(result, list)

    def test_mocked_fitz_failure_gracefully_degrades(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When fitz raises an exception, extract_text_from_pdf falls back to text decoding."""
        import sys

        # Create a mock fitz module that raises on open()
        class BrokenFitz:
            @staticmethod
            def open(*args: object, **kwargs: object) -> object:
                raise RuntimeError("Damaged PDF: stream corrupted")

        monkeypatch.setattr("app.features.profile.cv_parser._HAS_FITZ", True)
        monkeypatch.setitem(sys.modules, "fitz", BrokenFitz)

        text_content = b"Candidate knows Python and SQL"
        result = extract_text_from_pdf(text_content)
        assert "Python" in result
        assert "SQL" in result

    def test_empty_pdf_and_text_bytes(self) -> None:
        """Empty input bytes must return an empty list without error."""
        assert parse_cv("empty.pdf", b"") == []
        assert parse_cv("empty.txt", b"") == []
        assert extract_text("empty.pdf", b"") == ""

    def test_malformed_utf8_binary_replacement(self) -> None:
        """Bytes with non-UTF-8 characters should safely decode using replacement."""
        malformed = b"Python programmer with \xff\xfe\xfa SQL competence"
        skills = parse_cv("malformed.txt", malformed)
        ids = [s.skill_id for s in skills]
        assert "python" in ids
        assert "sql" in ids

    def test_null_bytes_and_control_characters(self) -> None:
        """Control characters and null bytes should be stripped during cleaning."""
        raw_dirty = b"Python\x00\x01\x02\x03 developer\r\n\x0bwith SQL skills\x0c"
        cleaned = clean_text(raw_dirty.decode("utf-8", errors="replace"))
        assert "\x00" not in cleaned
        assert "\x01" not in cleaned
        skills = parse_cv("dirty.txt", raw_dirty)
        ids = [s.skill_id for s in skills]
        assert "python" in ids
        assert "sql" in ids

    def test_punctuation_and_symbol_heavy_text(self) -> None:
        """Excessive symbols and punctuation should not break tokenization."""
        text = "Python!?!?! ... ::;;; --- (((SQL))) &&& [Excel] ***"
        skills = extract_skills(text)
        ids = [s.skill_id for s in skills]
        assert "python" in ids
        assert "sql" in ids
        assert "excel" in ids

    def test_text_with_only_numbers_and_noise(self) -> None:
        """Noise-only text should return no skills."""
        noise = "12345 67890 999-000-111 @#$%^&*()_+=-~`{}[]|"
        assert extract_skills(noise) == []

    def test_xss_and_code_injection_strings(self) -> None:
        """Injected code should be treated purely as string tokens without execution."""
        injection = "<script>alert('xss')</script> DROP TABLE skills;-- Python SQL"
        skills = extract_skills(injection)
        ids = [s.skill_id for s in skills]
        assert "python" in ids
        assert "sql" in ids


# ---------------------------------------------------------------------------
# Schema Validation & Fairness Whitelist Enforcement
# ---------------------------------------------------------------------------


class TestSchemaValidationAndDemographicFairness:
    def _base_questionnaire(self) -> dict:
        return {
            "segment": "graduate",
            "interests": ["data", "AI"],
            "hours_per_week": 10,
            "learning_style": "video",
            "budget_myr": 100.0,
            "hrd_eligible": False,
        }

    @pytest.mark.parametrize(
        "demographic_field,value",
        [
            ("gender", "female"),
            ("age", 26),
            ("race", "malay"),
            ("ethnicity", "chinese"),
            ("religion", "islam"),
            ("marital_status", "single"),
            ("nationality", "malaysian"),
        ],
    )
    def test_questionnaire_strictly_rejects_demographic_fields(
        self, demographic_field: str, value: object
    ) -> None:
        """Extra demographic attributes must trigger ValidationError per fairness whitelist."""
        payload = self._base_questionnaire()
        payload[demographic_field] = value
        with pytest.raises(pydantic.ValidationError) as exc_info:
            QuestionnaireIn.model_validate(payload)
        assert "extra_forbidden" in str(exc_info.value)

    def test_questionnaire_api_returns_422_on_demographic_field(self, client: TestClient) -> None:
        """Endpoint POST /profile/questionnaire returns 422 when demographic fields are sent."""
        payload = self._base_questionnaire()
        payload["gender"] = "male"
        resp = client.post("/api/v1/profile/questionnaire", json=payload, headers=WEIJIE)
        assert resp.status_code == 422

    def test_skill_edit_rejects_extra_fields(self) -> None:
        """SkillEdit rejects demographic or extra unauthorized keys."""
        with pytest.raises(pydantic.ValidationError) as exc_info:
            SkillEdit.model_validate({"skill_id": "python", "level": 3, "gender": "male"})
        assert "extra_forbidden" in str(exc_info.value)

    def test_skill_confirmation_in_rejects_extra_fields(self) -> None:
        """SkillConfirmationIn rejects extra top-level fields."""
        with pytest.raises(pydantic.ValidationError) as exc_info:
            SkillConfirmationIn.model_validate(
                {
                    "skills": [{"skill_id": "python", "level": 3}],
                    "user_demographics": {"race": "malay"},
                }
            )
        assert "extra_forbidden" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_hours", [-1, -10, 81, 100])
    def test_questionnaire_hours_per_week_boundaries(self, invalid_hours: int) -> None:
        payload = self._base_questionnaire()
        payload["hours_per_week"] = invalid_hours
        with pytest.raises(pydantic.ValidationError):
            QuestionnaireIn.model_validate(payload)

    def test_questionnaire_budget_cannot_be_negative(self) -> None:
        payload = self._base_questionnaire()
        payload["budget_myr"] = -0.01
        with pytest.raises(pydantic.ValidationError):
            QuestionnaireIn.model_validate(payload)

    @pytest.mark.parametrize("invalid_level", [-1, 0, 6, 7, 10])
    def test_skill_edit_level_must_be_between_1_and_5(self, invalid_level: int) -> None:
        with pytest.raises(pydantic.ValidationError):
            SkillEdit.model_validate({"skill_id": "python", "level": invalid_level})

    def test_questionnaire_missing_required_fields(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            QuestionnaireIn.model_validate({"segment": "graduate"})


# ---------------------------------------------------------------------------
# Persistence Math & Normalisation Edge Cases
# ---------------------------------------------------------------------------


class TestPersistenceMathAndNormalisationInvariants:
    @pytest.mark.parametrize(
        "level,expected_float",
        [
            (1, 0.0),
            (2, 0.25),
            (3, 0.50),
            (4, 0.75),
            (5, 1.0),
        ],
    )
    def test_exact_float_values(self, level: int, expected_float: float) -> None:
        """Ensures formula (level - 1) / 4.0 matches exact expected float values."""
        assert normalise_level(level) == expected_float

    def test_monotonicity_and_step_size(self) -> None:
        """Ensures each increase in level corresponds to exactly 0.25 increment."""
        for lvl in range(1, 5):
            delta = normalise_level(lvl + 1) - normalise_level(lvl)
            assert pytest.approx(delta, abs=1e-9) == 0.25

    def test_unit_interval_bounds(self) -> None:
        """Ensures all 1-5 levels map strictly inside [0.0, 1.0]."""
        for lvl in range(1, 6):
            val = normalise_level(lvl)
            assert 0.0 <= val <= 1.0

    def test_end_to_end_persistence_via_api(self, client: TestClient) -> None:
        """Validates that confirming levels 1 and 5 persists and normalises to 0.0 and 1.0."""
        payload = {
            "skills": [
                {"skill_id": "python", "level": 1, "source": "confirmed"},
                {"skill_id": "sql", "level": 5, "source": "confirmed"},
            ]
        }
        resp = client.put("/api/v1/profile/skills/confirm", json=payload, headers=WEIJIE)
        assert resp.status_code == 200
        data = resp.json()

        py_skill = next(s for s in data["normalised_skills"] if s["skill_id"] == "python")
        sql_skill = next(s for s in data["normalised_skills"] if s["skill_id"] == "sql")
        assert py_skill["normalised_level"] == 0.0
        assert sql_skill["normalised_level"] == 1.0

        # Query GET /profile/me to verify profile persistence
        me_resp = client.get("/api/v1/profile/me", headers=WEIJIE)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        saved_ids = {s["skill_id"]: s["level"] for s in me_data["skills"]}
        assert saved_ids["python"] == 1
        assert saved_ids["sql"] == 5


# ---------------------------------------------------------------------------
# Public Data (data/seed) Grounding & Provenance (arXiv & BLS)
# ---------------------------------------------------------------------------


class TestPublicDataFolderIntegration:
    """Verifies that all reference and test data derives from public data in src/data/seed.

    Datasets verified:
      - src/data/seed/bls_projections_2023_2033.csv (U.S. Bureau of Labor Statistics)
      - src/data/seed/arxiv_raw/ (arXiv cs.AI / cs.LG papers)
      - src/data/seed/taxonomy/skills.csv (Public taxonomy skills)
    """

    def test_bls_public_data_file_exists_and_valid(self) -> None:
        import csv
        from pathlib import Path

        seed_dir = Path(__file__).resolve().parents[3] / "src" / "data" / "seed"
        bls_path = seed_dir / "bls_projections_2023_2033.csv"
        assert bls_path.exists(), f"BLS public dataset missing: {bls_path}"

        with open(bls_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) > 50
        assert "soc_code" in rows[0]
        assert "occupation_title" in rows[0]

    def test_arxiv_public_data_cache_exists_and_valid(self) -> None:
        import json
        from pathlib import Path

        seed_dir = Path(__file__).resolve().parents[3] / "src" / "data" / "seed"
        arxiv_dir = seed_dir / "arxiv_raw"
        assert arxiv_dir.exists(), f"arXiv cache directory missing: {arxiv_dir}"

        json_files = list(arxiv_dir.glob("*.json"))
        assert len(json_files) >= 1, "At least one arXiv public data cache file must exist"

        with open(json_files[0], encoding="utf-8") as f:
            payload = json.load(f)
        assert isinstance(payload, (list, dict))

    def test_all_tested_profile_skills_exist_in_public_taxonomy(self) -> None:
        """Every skill ID tested in profile tests must exist in public taxonomy seed data."""
        from app.features.profile.cv_parser import _load_taxonomy

        tax = _load_taxonomy()
        tested_canonical_skills = ["python", "sql", "excel", "ai-literacy", "prompt-engineering"]
        for sid in tested_canonical_skills:
            assert sid in tax, f"Skill '{sid}' not in public seed taxonomy"
