"""Adi: grounded answers, checked references, flagged figures and an always-on fallback."""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.llm.provider import (
    LLMUnavailableError,
    NullProvider,
    OpenAICompatibleProvider,
    build_provider,
)
from app.features.assistant import context as ctx_mod
from app.features.assistant import guide, service

ASK = "/api/v1/assistant/chat"


class FakeProvider:
    name = "openai_compatible"
    model = "fake-model"

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.seen: list[dict[str, str]] = []

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 600) -> str:
        self.seen = messages
        return self.reply

    def complete_structured(self, system, prompt, schema):  # noqa: ANN001, ANN201
        raise LLMUnavailableError("not used")


def _ask(client: TestClient, text: str, **extra: object) -> dict:
    resp = client.post(ASK, json={"messages": [{"role": "user", "content": text}], **extra})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_guide_answers_without_a_model(client: TestClient) -> None:
    body = _ask(client, "What should I do next?")
    assert body["used_llm"] is False
    assert body["provider"] == "none"
    assert any(p["kind"] != "text" for p in body["parts"]), "guide links to roles/pages"
    assert body["suggestions"]


def test_visitor_gets_public_answers_without_signing_in(client: TestClient) -> None:
    resp = client.post(
        ASK,
        json={"messages": [{"role": "user", "content": "How does Adept work?"}]},
        headers={"X-Demo-User": ""},
    )
    assert resp.status_code == 200


def test_model_references_are_checked_and_unknown_ids_dropped(client: TestClient) -> None:
    fake = FakeProvider(
        "Try [[role:data-analyst]] and learn [[skill:sql]]. Also [[role:astronaut-ceo]]. "
        "See [[page:/app/pathway]]."
    )
    with patch.object(service, "_provider", return_value=fake):
        body = _ask(client, "Which role suits me?")
    assert body["used_llm"] is True
    refs = [(p["kind"], p["ref_id"]) for p in body["parts"] if p["kind"] != "text"]
    assert ("role", "data-analyst") in refs
    assert ("skill", "sql") in refs
    assert ("page", "/app/pathway") in refs
    assert all(r[1] != "astronaut-ceo" for r in refs), "invented role must never be shown"
    assert all("[[" not in p["text"] for p in body["parts"])
    role = next(p for p in body["parts"] if p["ref_id"] == "data-analyst")
    assert role["text"] == "Data Analyst", "label comes from the catalogue, not the model"


def test_figures_missing_from_the_data_are_flagged(client: TestClient) -> None:
    fake = FakeProvider("Data analysts earn RM 9,999 and demand grows 87% a year.")
    with patch.object(service, "_provider", return_value=fake):
        body = _ask(client, "Tell me about pay")
    assert body["unchecked_figures"], body


def test_question_is_redacted_before_the_model_sees_it(client: TestClient) -> None:
    fake = FakeProvider("Noted.")
    with patch.object(service, "_provider", return_value=fake):
        _ask(client, "My email is siti@example.com and IC 900101-14-5678, what next?")
    sent = fake.seen[-1]["content"]
    assert "siti@example.com" not in sent
    assert "900101-14-5678" not in sent


def test_model_failure_falls_back_to_the_guide(client: TestClient) -> None:
    class Broken(FakeProvider):
        def chat(self, messages, max_tokens=600):  # noqa: ANN001, ANN201
            raise LLMUnavailableError("down")

    with patch.object(service, "_provider", return_value=Broken("")):
        body = _ask(client, "What next?")
    assert body["used_llm"] is False
    assert body["parts"]


@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
def test_guide_speaks_each_language(client: TestClient, locale: str) -> None:
    body = _ask(client, "help", locale=locale)
    assert body["parts"]
    assert len(body["suggestions"]) == 3


def test_intents_match_three_languages() -> None:
    assert guide.intent("Is my CV stored?") == "privacy"
    assert guide.intent("Kursus mana boleh tuntut HRD Corp?") == "cost"
    assert guide.intent("哪些技能在上升？") == "trend"


def test_unchecked_figures_ignore_numbers_in_the_context() -> None:
    ctx = ctx_mod.Context(audience="learner", lines=["fit 72% and RM 450"])
    assert service.unchecked_figures("Your fit is 72% and it costs RM 450.", ctx) == []
    assert service.unchecked_figures("It costs RM 999.", ctx) == ["RM 999"]


# --- provider -------------------------------------------------------------------------------


def _transport(captured: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Hello!"}}]})

    return httpx.MockTransport(handler)


def test_openai_compatible_provider_posts_chat_completions() -> None:
    captured: dict = {}
    provider = OpenAICompatibleProvider(
        "runpod",
        "qwen",
        "https://api.runpod.ai/v2/abc/openai/v1",
        "key",
        transport=_transport(captured),
    )
    assert provider.chat([{"role": "user", "content": "hi"}]) == "Hello!"
    assert captured["url"] == "https://api.runpod.ai/v2/abc/openai/v1/chat/completions"
    assert captured["auth"] == "Bearer key"
    assert captured["body"]["max_tokens"] == 600


def test_openai_style_providers_send_max_completion_tokens() -> None:
    captured: dict = {}
    provider = OpenAICompatibleProvider(
        "replit", "gpt-x", "https://proxy.example/v1", "k", transport=_transport(captured)
    )
    provider.chat([{"role": "user", "content": "hi"}], max_tokens=50)
    assert captured["body"]["max_completion_tokens"] == 50
    assert "temperature" not in captured["body"]


def test_http_errors_become_unavailable() -> None:
    provider = OpenAICompatibleProvider(
        "openai",
        "m",
        "https://api.example/v1",
        "k",
        transport=httpx.MockTransport(lambda r: httpx.Response(429, json={})),
    )
    with pytest.raises(LLMUnavailableError):
        provider.chat([{"role": "user", "content": "hi"}])


def test_replit_provider_reads_injected_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_BASE_URL", "http://localhost:1106/openai")
    monkeypatch.setenv("AI_INTEGRATIONS_OPENAI_API_KEY", "replit-key")
    provider = build_provider(Settings(llm_provider="replit", llm_model="gpt-5.4-mini"))
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider._url == "http://localhost:1106/openai/chat/completions"


def test_provider_requires_a_model() -> None:
    from app.core.config import Settings

    with pytest.raises(LLMUnavailableError):
        build_provider(Settings(llm_provider="openai", llm_model=""))
    assert isinstance(build_provider(Settings(llm_provider="none")), NullProvider)
