"""Learning style is captured by the questionnaire and kept on the profile (F1)."""

from fastapi.testclient import TestClient


def _questionnaire(client: TestClient, user: str, **extra: object) -> dict:
    body = {
        "segment": "working",
        "interests": ["data"],
        "hours_per_week": 6,
        "budget_myr": 200,
        "hrd_eligible": True,
        **extra,
    }
    resp = client.post("/api/v1/profile/questionnaire", json=body, headers={"X-Demo-User": user})
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def test_learning_style_is_saved_and_returned(client: TestClient) -> None:
    out = _questionnaire(client, "aisyah", learning_style="hands-on")
    assert out["learning_style"] == "hands-on"
    me = client.get("/api/v1/profile/me", headers={"X-Demo-User": "aisyah"}).json()
    assert me["learning_style"] == "hands-on"


def test_profile_update_without_style_keeps_the_saved_choice(client: TestClient) -> None:
    _questionnaire(client, "weijie", learning_style="video")
    resp = client.post(
        "/api/v1/profile",
        json={
            "segment": "switcher",
            "interests": [],
            "hours_per_week": 4,
            "budget_myr": 0,
            "hrd_eligible": False,
        },
        headers={"X-Demo-User": "weijie"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["learning_style"] == "video"


def test_unknown_learning_style_is_rejected(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/profile/questionnaire",
        json={
            "segment": "working",
            "interests": [],
            "hours_per_week": 6,
            "budget_myr": 0,
            "hrd_eligible": False,
            "learning_style": "osmosis",
        },
        headers={"X-Demo-User": "aisyah"},
    )
    assert resp.status_code == 422
