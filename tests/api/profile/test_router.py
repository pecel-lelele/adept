import pytest
from fastapi.testclient import TestClient

from app.contracts.profile import CvExtractionResult, Profile

WEIJIE = {"X-Demo-User": "weijie"}


def test_get_my_profile_defaults_to_aisyah(client: TestClient) -> None:
    resp = client.get("/api/v1/profile/me")
    assert resp.status_code == 200
    assert Profile.model_validate(resp.json()).user_id == "aisyah"


def test_upsert_profile(client: TestClient) -> None:
    payload = {
        "segment": "graduate",
        "interests": ["AI"],
        "hours_per_week": 12,
        "budget_myr": 100,
        "hrd_eligible": False,
    }
    resp = client.post("/api/v1/profile", json=payload, headers=WEIJIE)
    assert resp.status_code == 200
    body = Profile.model_validate(resp.json())
    assert body.hours_per_week == 12


def test_upload_cv(client: TestClient) -> None:
    files = {"file": ("synthetic_cv.txt", b"Synthetic CV text", "text/plain")}
    resp = client.post("/api/v1/profile/cv", files=files)
    assert resp.status_code == 200
    body = CvExtractionResult.model_validate(resp.json())
    assert all(0 <= s.confidence <= 1 for s in body.skills)


def test_replace_skills(client: TestClient) -> None:
    skills = [{"skill_id": "python", "level": 3, "source": "confirmed"}]
    resp = client.put("/api/v1/profile/skills", json={"skills": skills}, headers=WEIJIE)
    assert resp.status_code == 200
    assert Profile.model_validate(resp.json()).skills[0].level == 3


def test_replace_skills_rejects_bad_level(client: TestClient) -> None:
    skills = [{"skill_id": "python", "level": 9, "source": "confirmed"}]
    resp = client.put("/api/v1/profile/skills", json={"skills": skills}, headers=WEIJIE)
    assert resp.status_code == 422


def test_upload_cv_rejects_oversized_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 1024)
    files = {"file": ("big.txt", b"x" * 2048, "text/plain")}
    resp = client.post("/api/v1/profile/cv", files=files)
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "payload_too_large"


def test_upload_cv_accepts_file_at_the_limit(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 1024)
    files = {"file": ("ok.txt", b"x" * 1024, "text/plain")}
    assert client.post("/api/v1/profile/cv", files=files).status_code == 200
