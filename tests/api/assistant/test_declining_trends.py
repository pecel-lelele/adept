import pytest

from app.features.assistant import context, guide
from app.features.trends import mocks
from app.features.trends import service as trends_service


@pytest.mark.parametrize(
    ("question", "locale"),
    [
        ("Which skills are declining?", "en"),
        ("What skills are losing demand?", "en"),
        ("Kemahiran apa yang semakin kurang diperlukan?", "ms"),
        ("未来哪些工作会消失？", "zh"),
    ],
)
def test_declining_questions_use_declining_facts_never_rising(question: str, locale: str) -> None:
    ctx = context.Context(
        audience="learner",
        facts={
            "rising": ["synthetic-rising"],
            "declining": ["synthetic-declining"],
            "declining_roles": ["synthetic-declining-role"],
        },
    )
    assert guide.intent(question) == "trend_declining"
    text = guide.reply(question, ctx, locale)
    assert "[[skill:synthetic-declining]]" in text
    assert "[[role:synthetic-declining-role]]" in text
    assert "synthetic-rising" not in text


def test_context_stores_declining_skills_and_roles_from_the_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = mocks.snapshot("moderate")
    monkeypatch.setattr(trends_service, "get_snapshot", lambda *_: snapshot)
    ctx = context.Context(audience="learner")
    context._trends(ctx, "moderate", set())
    assert ctx.facts["declining"]
    assert all(
        next(item for item in snapshot.items if item.skill_id == skill).direction_moderate
        == "declining"
        for skill in ctx.facts["declining"]
    )
    assert not set(ctx.facts["declining"]) & set(ctx.facts["rising"])
    assert ctx.facts["declining_roles"]


def test_insufficient_evidence_roles_are_not_called_declining(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = mocks.snapshot("moderate")
    real = trends_service.signals_from_snapshot(snapshot, "moderate")
    forced = [
        s.model_copy(update={"direction": "declining", "insufficient_evidence": True})
        if s.entity_type == "role"
        else s
        for s in real
    ]
    monkeypatch.setattr(trends_service, "get_snapshot", lambda *_: snapshot)
    monkeypatch.setattr(trends_service, "signals_from_snapshot", lambda *_: forced)
    ctx = context.Context(audience="learner")
    context._trends(ctx, "moderate", set())
    assert ctx.facts["declining_roles"] == []
