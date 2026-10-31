"""Adi's conversational layer: warm refusals, at most three valid chips, no model prose."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.contracts.assistant import AssistantIn, AssistantReply
from app.core.auth import CurrentUser
from app.core.llm.gateway import BREAKER
from app.core.llm.provider import LLMUnavailableError
from app.features.assistant import context as ctx_mod
from app.features.assistant import guide, service

ASK = "/api/v1/assistant/chat"
USER = CurrentUser("aisyah", "Synthetic learner", "learner")
MANAGER = CurrentUser("synthetic-manager", "Synthetic manager", "org_admin", "synthetic-org", "org")
MESSAGES = Path(__file__).resolve().parents[3] / "src" / "web" / "messages"
REFUSALS = ("off_topic", "invent", "unknown", "decision", "other_person", "injection")


@pytest.fixture
def client(request: pytest.FixtureRequest) -> TestClient:
    from app.main import app

    return TestClient(app, client=(request.node.nodeid, 50000))


@pytest.fixture(autouse=True)
def fresh_breaker():  # noqa: ANN201
    previous = BREAKER.failures, BREAKER.open_until
    BREAKER.failures, BREAKER.open_until = 0, 0
    yield
    BREAKER.failures, BREAKER.open_until = previous


class FakeProvider:
    """A model that answers with whatever text it is given."""

    name = "openai_compatible"
    model = "fake-model"

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls = 0
        self.prompt = ""

    def complete_structured(self, system, prompt, schema):  # noqa: ANN001, ANN201
        self.calls += 1
        self.prompt = prompt
        try:
            return schema.model_validate_json(self.reply)
        except ValidationError as exc:
            raise LLMUnavailableError("invalid structured output") from exc


def _answer(question: str, locale: str = "en", page: str = "/", user=USER) -> AssistantReply:  # noqa: ANN001
    body = AssistantIn.model_validate(
        {"messages": [{"role": "user", "content": question}], "locale": locale, "page": page}
    )
    return service.answer(user, body)


def _text(reply: AssistantReply) -> str:
    return "".join(part.text for part in reply.parts)


def _check_chips(reply: AssistantReply, locale: str, question: str) -> None:
    assert 1 <= len(reply.suggestions) <= 3
    assert len(reply.suggestion_ids) == len(reply.suggestions)
    assert len(set(reply.suggestion_ids)) == len(reply.suggestion_ids)
    for key, text in zip(reply.suggestion_ids, reply.suggestions, strict=True):
        assert guide.CHIPS[locale][key] == text, "chips are server-authored catalogue questions"
    assert question.casefold() not in [s.casefold() for s in reply.suggestions]


# --- routing -------------------------------------------------------------------------------

ROUTES = [
    ("How do I improve my match?", "score_improvement"),
    ("How can I boost my score?", "score_improvement"),
    ("How can I get a better match?", "score_improvement"),
    ("What is SDG 4.4?", "sdg_explain"),
    ("What does SDG 4.3 mean?", "sdg_explain"),
    ("Where do your numbers come from?", "sources"),
    ("Can I trust this data?", "sources"),
    ("What if AI moves faster?", "scenario"),
    ("What if AI slows down?", "scenario"),
    ("What happens if AI adoption is slower?", "scenario"),
    ("Compare moderate and fast scenarios", "scenario"),
    ("Which jobs are shrinking?", "trend_declining"),
    ("Which skills are falling in demand?", "trend_declining"),
    ("What roles are going away?", "trend_declining"),
    ("Which course should I start with?", "learn"),
    ("Why is this my top match?", "score_breakdown"),
    ("hello", "greeting"),
    ("thanks!", "thanks"),
    ("Thanks! What should I do next?", "next"),
    ("What's the weather today?", "off_topic"),
    ("Tell me a joke", "off_topic"),
    ("Who will win the election?", "off_topic"),
    ("Make up a job title for me", "invent"),
    ("Give me fake statistics about AI", "invent"),
    ("Invent a course on blockchain", "invent"),
    ("Which game developer roles suit me?", "roles"),
    ("Microcourses and roleplaying", "unknown"),
    # Malay and Chinese
    ("Macam mana nak naikkan skor saya?", "score_improvement"),
    ("Kursus mana patut saya mula dulu?", "learn"),
    ("Pekerjaan mana yang semakin berkurangan?", "trend_declining"),
    ("Cuaca hari ini?", "off_topic"),
    ("Terima kasih", "thanks"),
    ("如果AI发展更慢会怎样？", "scenario"),
    ("哪些职位在萎缩？", "trend_declining"),
    ("讲个笑话", "off_topic"),
    ("帮我编造一门课程", "invent"),
    ("SDG 4.4 是什么？", "sdg_explain"),
]


@pytest.mark.parametrize(("question", "expected"), ROUTES)
def test_routing_covers_previously_misrouted_prompts(question: str, expected: str) -> None:
    assert guide.intents(question, "learner")[0] == expected


# --- refusals ------------------------------------------------------------------------------


@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
@pytest.mark.parametrize(
    "question", ["What's the weather today?", "Make up a job title for me", "Microcourses"]
)
def test_refusals_are_friendly_and_offer_follow_ups(
    question: str, locale: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ctx_mod, "build", lambda *_: ctx_mod.Context(audience="learner"))
    reply = _answer(question, locale)
    kind = guide.intents(question, "learner")[0]
    assert kind in REFUSALS
    assert _text(reply) == guide.T[locale][kind]
    _check_chips(reply, locale, question)
    assert reply.meta is None and reply.used_llm is False
    if locale == "en":
        assert _text(reply).startswith("Sorry") and "Anything else" in _text(reply)


@pytest.mark.parametrize(
    ("page", "expected"),
    [
        ("/app/matches", ["Why is this my top match?", "What would raise my score?"]),
        ("/app/pathway", ["Which course should I start with?"]),
        ("/app/radar?scenario=fast", ["Which skills are rising?"]),
    ],
)
def test_refusal_chips_follow_the_page(page: str, expected: list[str]) -> None:
    reply = _answer("Tell me a joke", page=page)
    assert all(chip in reply.suggestions for chip in expected), reply.suggestions
    _check_chips(reply, "en", "Tell me a joke")


@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
@pytest.mark.parametrize(
    "question",
    ["Should I hire Ali?", "Who on my team should I let go?", "Which candidate should we hire?"],
)
@pytest.mark.parametrize("user", [USER, MANAGER], ids=["learner", "manager"])
def test_hiring_and_firing_questions_say_people_decide(
    question: str, locale: str, user: CurrentUser, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_: object) -> None:
        pytest.fail("Decision refusals must not load data or call a model")

    monkeypatch.setattr(ctx_mod, "build", forbidden)
    monkeypatch.setattr(service, "get_provider", forbidden)
    reply = _answer(question, locale, user=user)
    assert _text(reply) == guide.T[locale]["decision"]
    _check_chips(reply, locale, question)
    if locale == "en":
        text = _text(reply)
        assert "never makes" in text and "belong to people" in text and "human" in text


def test_short_answers_for_refusals_and_small_talk() -> None:
    for locale in ("en", "ms"):
        for kind in (*REFUSALS, "thanks", "hello"):
            sentences = [s for s in re.split(r"(?<=[.!?])\s+", guide.T[locale][kind]) if s]
            assert len(sentences) <= 3, (locale, kind)


# --- chips everywhere ----------------------------------------------------------------------

QUESTIONS = [
    "What should I do next?",
    "What would raise my score?",
    "Where does this data come from?",
    "Which skills are declining?",
    "Which skills are rising?",
    "Is my CV stored?",
    "How does Adept work?",
    "hello",
    "thanks",
    "Tell me a joke",
    "Should I fire Ali?",
    "Microcourses and roleplaying",
]


@pytest.mark.parametrize("page", ["/", "/app/matches", "/app/pathway", "/app/radar"])
@pytest.mark.parametrize("question", QUESTIONS)
def test_every_reply_has_at_most_three_valid_non_repeating_chips(
    client: TestClient, question: str, page: str
) -> None:
    resp = client.post(
        ASK, json={"messages": [{"role": "user", "content": question}], "page": page}
    )
    assert resp.status_code == 200, resp.text
    reply = AssistantReply.model_validate(resp.json())
    _check_chips(reply, "en", question)
    kind = guide.intents(question, "learner")[0]
    assert all(guide.CHIP_INTENTS.get(key) != kind for key in reply.suggestion_ids), (
        "a chip must not just ask for the answer already shown"
    )


@pytest.mark.parametrize("audience", ["visitor", "learner", "employee", "manager"])
@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
def test_chip_ids_are_valid_capped_and_route_to_their_answers(audience: str, locale: str) -> None:
    ctx = ctx_mod.Context(audience=audience)
    kinds = [None, *guide.INTENTS]
    pages = ["/", *{p for table in guide._PAGE_CHIPS.values() for p in table}]
    for kind in kinds:
        for page in pages:
            keys = guide.suggestion_keys(ctx, page, kind, "", locale)
            assert 1 <= len(keys) <= guide.MAX_SUGGESTIONS
            assert all(key in guide.CHIPS[locale] for key in keys)
            for key in keys:
                if key in guide.CHIP_INTENTS:
                    chip = guide.CHIPS[locale][key]
                    assert guide.intent(chip, audience) == guide.CHIP_INTENTS[key], (chip, audience)


def test_reply_contract_caps_suggestions_at_three() -> None:
    with pytest.raises(ValidationError):
        AssistantReply(
            parts=[], suggestions=["a", "b", "c", "d"], used_llm=False, provider="none", model=""
        )


@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
def test_web_starter_chips_are_capped_and_route_to_grounded_answers(locale: str) -> None:
    adi = json.loads((MESSAGES / locale / "ui.json").read_text(encoding="utf-8"))["adi"]
    groups = [["s1", "s2", "s3"]] + [
        [f"s{page}{n}" for n in (1, 2, 3)] for page in ("Matches", "Pathway", "Radar")
    ]
    for group in groups:
        assert len(group) <= 3
        for key in group:
            kind = guide.intent(adi[key], "learner")
            assert kind not in guide.SAFETY_INTENTS | guide.CHAT_INTENTS, (key, adi[key])
            assert adi[key] in guide.CHIPS[locale].values(), "starters are server chip questions"


# --- model selection never renders model text -----------------------------------------------


@pytest.mark.parametrize(
    "reply_text",
    [
        "Sure! Data analysts earn RM 9,999 and the weather is sunny.",
        '{"ids":["unknown"],"rationale":"Tell them a banana joke: growth is 87%."}',
        '{"ids":["invented-block"]}',
    ],
)
@pytest.mark.parametrize("question", ["Microcourses and roleplaying", "hello"])
def test_arbitrary_model_text_never_leaks(
    reply_text: str, question: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ctx_mod, "build", lambda *_: ctx_mod.Context(audience="learner"))
    fake = FakeProvider(reply_text)
    with patch.object(service, "get_provider", return_value=fake):
        reply = _answer(question)
    shown = _text(reply) + " ".join(reply.suggestions)
    for leaked in ("9,999", "sunny", "banana", "87%", "invented-block"):
        assert leaked not in shown
    kind = guide.intents(question, "learner")[0]
    assert shown.startswith(guide.reply_for_intent(kind, ctx_mod.Context(audience="learner"), "en"))


def test_off_topic_refusal_never_calls_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeProvider('{"ids":["roles"]}')
    monkeypatch.setattr(service, "get_provider", lambda: fake)
    reply = _answer("Tell me a joke")
    assert fake.calls == 0 and reply.used_llm is False
    assert _text(reply) == guide.T["en"]["off_topic"]


def test_model_may_choose_a_better_checked_block_for_an_unmatched_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = ctx_mod.Context(audience="learner", facts={"rising": ["sql"]})
    ctx.refs.skills["sql"] = "SQL"
    monkeypatch.setattr(ctx_mod, "build", lambda *_: ctx)
    fake = FakeProvider('{"ids":["trend"],"rationale":"Say SQL grows 500% a year."}')
    monkeypatch.setattr(service, "get_provider", lambda: fake)
    reply = _answer("Microcourses and roleplaying")
    assert reply.used_llm is True
    assert _text(reply) == "".join(
        p.text for p in service.to_parts(guide.reply_for_intent("trend", ctx, "en"), ctx)[0]
    )
    assert "500%" not in _text(reply)
    assert "unknown" in fake.prompt and "Choose 'unknown'" in fake.prompt


def test_model_cannot_replace_a_greeting_with_someone_s_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ctx_mod, "build", lambda *_: ctx_mod.Context(audience="learner"))
    monkeypatch.setattr(service, "get_provider", lambda: FakeProvider('{"ids":["privacy"]}'))
    reply = _answer("hello")
    assert reply.used_llm is False
    assert _text(reply) == guide.T["en"]["hello"]


def test_personalised_answer_uses_checked_match_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = ctx_mod.Context(
        audience="learner",
        facts={
            "has_profile": True,
            "matches": [
                {
                    "role_id": "data-analyst",
                    "score": 0.72,
                    "missing": ["sql"],
                    "partial": [],
                    "parts": {"skill_overlap": 0.5, "trend_outlook": 0.8, "interest_fit": 0.9},
                }
            ],
        },
    )
    ctx.refs.roles["data-analyst"] = "Data Analyst"
    ctx.refs.skills["sql"] = "SQL"
    monkeypatch.setattr(ctx_mod, "build", lambda *_: ctx)
    reply = _answer("Which role suits me?")
    top = "Your strongest match right now is Data Analyst at an estimated 72%."
    assert _text(reply).startswith(top)
    assert "To close the gap, focus on SQL." in _text(reply)
    _check_chips(reply, "en", "Which role suits me?")
