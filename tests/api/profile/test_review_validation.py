"""Additional acceptance checks for the thirteen PR #4 review items."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.features.profile import cv_parser

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("suffix", ["", "@"])
def test_full_parse_of_email_adversarial_input_under_one_second(suffix: str) -> None:
    start = time.perf_counter()
    parsed, truncated = cv_parser.parse_cv(("a" * 50_000 + suffix).encode(), "text/plain")
    elapsed = time.perf_counter() - start
    print(f"parse 50000 a characters + {suffix!r}: {elapsed:.6f}s")
    assert elapsed < 1.0, f"Full parse exceeded 1s: {elapsed:.6f}s"
    assert parsed == []
    assert truncated is False


def test_upload_cap_is_five_mebibytes() -> None:
    assert get_settings().max_upload_bytes == 5 * 1024 * 1024


def test_route_reports_truncation_and_does_not_persist_skills(client: TestClient) -> None:
    before_response = client.get("/api/v1/profile/me")
    assert before_response.status_code == 200
    before = before_response.json()
    response = client.post(
        "/api/v1/profile/cv",
        files={
            "file": ("long.txt", b"x" * 200_000 + b" Python programming", "text/plain"),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["truncated"] is True
    assert response.json()["skills"] == []
    after_response = client.get("/api/v1/profile/me")
    assert after_response.status_code == 200
    assert after_response.json() == before


def test_data_entry_cannot_match_analysis_alias() -> None:
    parsed, _ = cv_parser.parse_cv(b"Experienced in data entry.", "text/plain")
    assert "data-visualisation" not in {skill.skill_id for skill in parsed}
    assert parsed == []


def test_java_boundary_with_explicit_test_only_taxonomy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Java is absent from the real catalogue; test the scanner with an injected catalogue."""
    taxonomy = {
        "java": cv_parser.TaxonomySkill("java", "Java", "java"),
        "javascript": cv_parser.TaxonomySkill("javascript", "JavaScript", "javascript"),
    }
    monkeypatch.setattr(cv_parser, "_load_taxonomy", lambda: taxonomy)
    cv_parser._build_alias_index.cache_clear()
    try:
        matches = cv_parser.extract_skills("Java and JavaScript")
        assert {skill.skill_id for skill in matches} == set(taxonomy)
        assert len(matches) == 2
        assert all(skill.confidence == pytest.approx(0.30) for skill in matches)
    finally:
        cv_parser._build_alias_index.cache_clear()


def test_generator_two_runs_have_identical_hashes(tmp_path: Path) -> None:
    command = [
        sys.executable,
        str(ROOT / "src/scripts/generate_mock_cvs.py"),
        "--out",
        str(tmp_path),
    ]
    hashes = []
    for _ in range(2):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        hashes.append(
            {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in tmp_path.iterdir()
                if path.is_file()
            }
        )
    assert len(hashes[0]) == 8
    assert hashes[0] == hashes[1]
    print("Generator executed twice: 8/8 SHA-256 hashes identical")
    for name, digest in sorted(hashes[0].items()):
        print(f"{name}: {digest}")
