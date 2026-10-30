"""Adi answers inside the workspace it was asked in (M4-033)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from harness.workspaces import BANK, accept_work_plan, work_headers

from app.features.assistant import guide
from app.features.assistant.context import Context

ASK = "/api/v1/assistant/chat"
ROLE = "process-automation-analyst"


def _ask(client: TestClient, text: str, headers: dict[str, str]) -> dict:
    body = {"messages": [{"role": "user", "content": text}]}
    resp = client.post(ASK, json=body, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _text(body: dict) -> str:
    return "".join(p["text"] for p in body["parts"])


def _hrefs(body: dict) -> set[str]:
    return {p["href"] for p in body["parts"] if p.get("href")}


def test_a_finished_plan_is_not_answered_with_save_a_plan() -> None:
    ctx = Context(audience="learner")
    ctx.facts.update(
        {
            "has_profile": True,
            "plan_role": ROLE,
            "plan_steps": [{"skill": "rpa", "courses": ["a", "b"]}],
            "done": ["a", "b"],
            "plan_progress": {"share": 1.0, "courses": 2, "gap_closed": 2, "gap_total": 3},
        }
    )
    text = guide.reply_for_intent("next", ctx, "en")
    assert "completed every course" in text and "1 required skill" in text
    assert "save a plan" not in text.lower()


def test_personal_answers_never_include_organisation_programmes(client: TestClient) -> None:
    accept_work_plan(ROLE)
    personal = _ask(
        client, "What should I do next?", {"X-Demo-User": "aisyah", "X-Workspace": "personal"}
    )
    assert personal["workspace"] == "personal" and personal["workspace_name"] == ""
    assert not any(h.startswith("/work") for h in _hrefs(personal))
    assert "Demo Bank" not in _text(personal)


def test_organisation_answers_name_the_organisation_and_its_programme(client: TestClient) -> None:
    accept_work_plan(ROLE)
    body = _ask(client, "What should I do next?", work_headers())
    assert body["workspace"] == BANK and body["workspace_name"] == "Demo Bank Berhad"
    text = _text(body)
    assert "Demo Bank Berhad" in text and "Test programme" in text
    assert "/work/progress" in _hrefs(body)
    roles = _ask(client, "Which roles match me?", work_headers())
    assert "personal workspace" in _text(roles)


def test_employees_learn_what_their_employer_can_see(client: TestClient) -> None:
    body = _ask(client, "What does my employer see?", work_headers())
    text = _text(body)
    assert "Demo Bank Berhad sees your programme progress" in text
    assert "skill levels you chose to share" in text
    assert "/work/skills" in _hrefs(body)


def test_no_programme_yet_is_stated(client: TestClient) -> None:
    body = _ask(client, "What should I do next?", work_headers())
    assert "has not sent you a programme yet" in _text(body)


def test_managers_hear_about_sent_programmes_not_a_default_team_plan(client: TestClient) -> None:
    hr = {"X-Demo-User": "demo-company", "X-Workspace": BANK}
    body = _ask(client, "How is my team doing?", hr)
    text = _text(body)
    assert "Too few members to show team skill gaps" in text
    assert "largest average gap" not in text
    assert "No programme sent yet" in text
    assert "share their skill levels" in text
    assert body["workspace_name"] == "Demo Bank Berhad"
