"""Verify guest preview boundaries without network or profile writes."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.contracts.common import RecommendationMeta, Source
from app.contracts.profile import CvExtractionResult, ExtractedSkill
from app.features.matching.scoring import Role, RoleSkill
from app.features.matching.trend_port import TrendSnapshot
from app.features.preview import router as preview
from app.main import app

SOURCE = Source(
    name="Test public source", url="https://example.org/source", retrieved_at=date(2024, 10, 20)
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        preview,
        "extract_cv",
        lambda *args, **kwargs: CvExtractionResult(
            skills=[ExtractedSkill(skill_id="python", label="Python", level=2, confidence=0.8)],
            meta=RecommendationMeta(
                sources=[SOURCE],
                snapshot_date=SOURCE.retrieved_at,
                scenario="moderate",
                is_estimate=True,
            ),
        ),
    )
    monkeypatch.setattr(
        preview,
        "fetch_snapshot",
        lambda scenario: TrendSnapshot(
            velocities={"python": 0.1},
            sources=[SOURCE],
            snapshot_date=SOURCE.retrieved_at,
            scenario=scenario,
            is_estimate=True,
        ),
    )
    monkeypatch.setattr(
        preview,
        "load_roles",
        lambda: [
            Role("data-analyst", (RoleSkill("python", 1.0, 3),)),
            Role("ai-operations-specialist", (RoleSkill("python", 1.0, 4),)),
        ],
    )
    return TestClient(app)


def test_anonymous_response_contains_only_one_role(client):
    response = client.post(
        "/api/v1/preview/cv",
        data={"synthetic_consent": "true"},
        files={"file": ("synthetic.txt", b"Python", "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["top_role"]["role_id"] == "data-analyst"
    assert body["other_role_count"] == 1
    assert "matches" not in body
    assert "missing_skills" not in body["top_role"]
    assert body["requires_skill_confirmation"] is True
    assert body["meta"]["snapshot_date"] == "2024-10-20"


def test_requires_synthetic_consent(client):
    response = client.post(
        "/api/v1/preview/cv",
        data={"synthetic_consent": "false"},
        files={"file": ("synthetic.txt", b"Python", "text/plain")},
    )
    assert response.status_code == 422


def test_rejects_other_formats(client):
    response = client.post(
        "/api/v1/preview/cv",
        data={"synthetic_consent": "true"},
        files={"file": ("cv.html", b"<p>Python</p>", "text/html")},
    )
    assert response.status_code == 415


def test_no_skill_extraction_does_not_rank(client, monkeypatch):
    monkeypatch.setattr(
        preview,
        "extract_cv",
        lambda *args, **kwargs: CvExtractionResult(
            skills=[],
            meta=RecommendationMeta(
                sources=[SOURCE],
                snapshot_date=SOURCE.retrieved_at,
                scenario="moderate",
                is_estimate=True,
            ),
        ),
    )
    monkeypatch.setattr(preview, "fetch_snapshot", lambda scenario: pytest.fail("must not fetch"))
    body = client.post(
        "/api/v1/preview/cv",
        data={"synthetic_consent": "true"},
        files={"file": ("synthetic.txt", b"No skills", "text/plain")},
    ).json()
    assert body["top_role"] is None
    assert body["other_role_count"] == 0
