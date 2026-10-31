"""Routing regression: each realistic question reaches the answer block it asks for.

Cases live in fixtures/routing_cases.tsv (question, audience, accepted intents joined by "|").
"""

from pathlib import Path

import pytest

from app.contracts.assistant import AssistantIn
from app.core.auth import CurrentUser
from app.core.llm.provider import NullProvider
from app.features.assistant import context, guide, service

CASES_FILE = Path(__file__).parent / "fixtures" / "routing_cases.tsv"


def _load() -> list[tuple[str, str, frozenset[str]]]:
    rows: list[tuple[str, str, frozenset[str]]] = []
    for line in CASES_FILE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        question, audience, accepted = line.split("\t")
        rows.append((question, audience, frozenset(accepted.split("|"))))
    return rows


CASES = _load()


def test_fixture_has_enough_cases() -> None:
    assert len(CASES) >= 80


@pytest.mark.parametrize(("question", "audience", "accepted"), CASES)
def test_routes_to_accepted_intent(question: str, audience: str, accepted: frozenset[str]) -> None:
    got = guide.intents(question, audience)
    assert got[0] in accepted, f"{question!r} -> {got}, accepted {sorted(accepted)}"


def test_action_not_supported_names_every_unsupported_action() -> None:
    actions = {
        "en": ("enrol", "book", "apply", "change your plan"),
        "ms": ("mendaftarkan", "menempah", "memohon", "mengubah pelan"),
        "zh": ("报名", "预订", "申请", "修改计划"),
    }
    for locale, verbs in actions.items():
        text = guide.T[locale]["action_not_supported"]
        assert all(verb in text for verb in verbs)
        assert "[[page:/app/pathway]]" in text
        assert "[[page:/app/jobs]]" in text


@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
def test_profile_reply_lists_own_saved_skills(locale: str) -> None:
    ctx = context.build(CurrentUser("weijie", "Synthetic learner", "learner"), "moderate")
    parts, rejected = service.to_parts(guide.reply("What skills do I have?", ctx, locale), ctx)
    assert not rejected
    assert {p.ref_id for p in parts if p.kind == "skill"} == set(ctx.facts["skills"])
    assert "[[page:/app/profile]]" in guide.reply_for_intent("profile", ctx, locale)


def test_named_match_reply_does_not_explain_a_different_role() -> None:
    ctx = context.build(CurrentUser("weijie", "Synthetic learner", "learner"), "moderate")
    target = ctx.facts["matches"][-1]
    question = f"Why is {target['role_id'].replace('-', ' ')} my top match?"
    parts, rejected = service.to_parts(guide.reply(question, ctx, "en"), ctx)
    assert not rejected
    assert next(p.ref_id for p in parts if p.kind == "role") == target["role_id"]
    assert f"{target['score'] * 100:.1f}" in "".join(p.text for p in parts)


def test_full_catalogue_label_with_parentheses_resolves_the_requested_role() -> None:
    ctx = context.build(CurrentUser("weijie", "Synthetic learner", "learner"), "moderate")
    target = ctx.facts["matches"][-1]
    label = ctx.refs.roles[target["role_id"]]
    focused = guide.focus_context(f"Why is {label} my top match?", ctx)
    assert focused.facts["focus_role"] == target["role_id"]
    assert "focus_role" not in ctx.facts, "focusing must preserve the shared context"


def test_named_role_without_loaded_match_does_not_reuse_top_score() -> None:
    ctx = context.build(CurrentUser("weijie", "Synthetic learner", "learner"), "moderate")
    ctx.facts["matches"] = [m for m in ctx.facts["matches"] if m["role_id"] != "data-engineer"]
    text = guide.reply("How can I improve my match for data engineer?", ctx, "en")
    assert "[[role:data-engineer]]" in text
    assert "couldn't load" in text
    assert "Total:" not in text


@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
def test_sdg_goal_question_only_lists_that_goals_targets(locale: str) -> None:
    ctx = context.build(CurrentUser("weijie", "Synthetic learner", "learner"), "moderate")
    parts, rejected = service.to_parts(guide.reply("What is SDG 4?", ctx, locale), ctx)
    assert not rejected
    targets = [p.ref_id for p in parts if p.kind == "sdg"]
    assert targets and all(target.startswith("4.") for target in targets)


@pytest.mark.parametrize(
    ("locale", "privacy_words"),
    [
        ("en", ("personal plans", "programme progress")),
        ("ms", ("Pelan peribadi", "kemajuan program")),
        ("zh", ("个人计划", "项目进度")),
    ],
)
def test_personal_privacy_reply_explains_employer_visibility(
    locale: str, privacy_words: tuple[str, str]
) -> None:
    text = guide.reply(
        "Can my employer see my progress?", context.Context(audience="learner"), locale
    )
    assert all(word in text for word in privacy_words)


def test_learning_question_about_python_does_not_redirect_to_sql() -> None:
    ctx = context.build(CurrentUser("weijie", "Synthetic learner", "learner"), "moderate")
    ctx.facts.update(plan_role="data-analyst", plan_steps=[{"skill": "sql", "courses": []}])
    text = guide.reply("Is learning Python worth it?", ctx, "en")
    assert "[[skill:python]]" in text
    assert "[[skill:sql]]" not in text


def test_hiring_question_points_to_openings_not_only_fit_scores() -> None:
    ctx = context.build(CurrentUser("weijie", "Synthetic learner", "learner"), "moderate")
    text = guide.reply("Which roles are hiring?", ctx, "en")
    assert "[[page:/app/jobs]]" in text


def test_capability_answer_cannot_be_replaced_by_unrelated_model_selection() -> None:
    assert service._accept(["learn"], guide.intents("What can you do?")) is None


def test_near_tie_does_not_allow_an_unrouted_second_block() -> None:
    assert service._accept(["cost", "roles"], ["cost", "learn"]) == ["cost", "learn"]


@pytest.mark.parametrize(
    "question",
    [
        "Which game developer roles suit me?",
        "Which stock analyst skills should I learn?",
        "Can I transition into cloud engineering?",
    ],
)
def test_unresolved_career_subject_does_not_show_another_roles_plan(question: str) -> None:
    ctx = context.build(CurrentUser("weijie", "Synthetic learner", "learner"), "moderate")
    text = guide.reply(question, ctx, "en")
    assert "[[page:/app/matches]]" in text
    assert "[[role:" not in text and "[[course:" not in text


@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
def test_self_enrolment_reply_explains_provider_sign_up(locale: str) -> None:
    ctx = context.Context(audience="learner")
    text = guide.reply("How do I enrol in a course myself?", ctx, locale)
    assert "[[page:/app/courses]]" in text
    assert text == guide.T[locale]["self_enrolment"]


@pytest.mark.parametrize(
    ("question", "expected_locale"),
    [
        ("Data trend ini dikemas kini bila?", "ms"),
        ("趋势数据最近什么时候更新？", "zh"),
    ],
)
def test_new_phrasings_reply_in_the_questions_language(question: str, expected_locale: str) -> None:
    assert guide.reply_locale(question, "en") == expected_locale


@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
@pytest.mark.parametrize("skills", [None, {}])
def test_missing_or_empty_profile_skills_are_not_invented(
    locale: str, skills: dict[str, int] | None
) -> None:
    ctx = context.Context(audience="learner", facts={"skills": skills})
    text = guide.reply_for_intent("profile", ctx, locale)
    assert guide.T[locale]["profile_unavailable" if skills is None else "profile_empty"] in text
    assert "[[skill:" not in text


@pytest.mark.parametrize("audience", ["employee", "manager"])
def test_org_profile_reply_does_not_disclose_personal_skills(audience: str) -> None:
    ctx = context.Context(audience=audience, facts={"skills": {"synthetic-private-skill": 3}})
    text = guide.reply_for_intent("profile", ctx, "en")
    assert "synthetic-private-skill" not in text
    assert "[[page:/work/skills]]" in text


@pytest.mark.parametrize("model_enabled", [False, True])
def test_same_rendered_near_tie_block_is_shown_once(
    model_enabled: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = CurrentUser("weijie", "Synthetic learner", "learner")
    ctx = context.build(user, "moderate")
    question = "Which game developer roles suit my skills?"
    assert guide.intents(question) == ["learn", "roles"]
    monkeypatch.setattr(context, "build", lambda *_: ctx)
    provider = NullProvider()
    if model_enabled:
        monkeypatch.setattr(provider, "name", "synthetic-test-provider")
        monkeypatch.setattr(
            service, "select_ids_or_fallback", lambda *_: (["learn", "roles"], True)
        )
    monkeypatch.setattr(service, "get_provider", lambda: provider)
    reply = service.answer(
        user, AssistantIn.model_validate({"messages": [{"role": "user", "content": question}]})
    )
    expected, rejected = service.to_parts(guide.T["en"]["role_exploration"], ctx)
    assert not rejected
    assert reply.parts == expected
    assert reply.used_llm == model_enabled
