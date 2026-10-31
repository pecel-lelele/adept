"""Adi's how-to blocks: paraphrases route to the right fixed, link-bearing answer."""

from __future__ import annotations

import re

import pytest

from app.features.assistant import context as ctx_mod
from app.features.assistant import guide, help_topics

# (question, audience, expected block)
PARAPHRASES = [
    ("where to upload cv", "learner", "help_cv_upload"),
    ("Where do I upload my CV?", "learner", "help_cv_upload"),
    ("how do I add my resume", "learner", "help_cv_upload"),
    ("can I attach my resume as a pdf", "learner", "help_cv_upload"),
    ("wher do i uplaod my resumee", "learner", "help_cv_upload"),
    ("Di mana nak muat naik CV?", "learner", "help_cv_upload"),
    ("在哪里上传简历？", "learner", "help_cv_upload"),
    ("where can my team members upload their cv", "manager", "help_cv_upload"),
    ("change my target role", "learner", "help_target_role"),
    ("how do I choose a role to aim for", "learner", "help_target_role"),
    ("I want to pick a different target role", "learner", "help_target_role"),
    ("Bagaimana pilih peranan sasaran?", "learner", "help_target_role"),
    ("如何选择目标职位？", "learner", "help_target_role"),
    ("where is the matches page", "learner", "help_matches"),
    ("what does the percentage on a match card mean", "learner", "help_matches"),
    ("how do I create a learning plan", "learner", "help_plan"),
    ("where can I see my pathway", "learner", "help_plan"),
    ("how do I mark a course as done", "learner", "help_progress"),
    ("where do I upload my certificate as evidence", "learner", "help_progress"),
    ("where are the job openings", "learner", "help_jobs"),
    ("where can I browse courses", "learner", "help_courses"),
    ("where do I see my SDG impact", "learner", "help_impact"),
    ("what is MyCOL", "learner", "help_impact"),
    ("which AI model do you use", "learner", "help_about"),
    ("how do I use a join code", "learner", "help_join_org"),
    ("how do I switch workspace", "employee", "help_workspaces"),
    ("how do I stop sharing my skills with my employer", "employee", "help_sharing"),
    ("how do I change the language", "learner", "help_languages"),
    ("Bagaimana tukar bahasa?", "learner", "help_languages"),
    ("how do I sign out", "learner", "help_account"),
    ("I forgot my password", "learner", "help_account"),
    ("where is the radar", "learner", "help_radar"),
    ("what can I ask you", "learner", "help_index"),
    ("how do I create a programme for my team", "manager", "help_org"),
]


@pytest.mark.parametrize(("question", "audience", "expected"), PARAPHRASES)
def test_paraphrases_route_to_their_help_block(question: str, audience: str, expected: str) -> None:
    assert expected in guide.intents(question, audience)[:2], guide.intents(question, audience)
    assert guide.intents(question, audience)[0] == expected


@pytest.mark.parametrize("question", ["Is my CV stored?", "Who can see my CV?", "Delete my CV"])
def test_cv_privacy_questions_stay_privacy_questions(question: str) -> None:
    assert guide.intents(question, "learner")[0] == "privacy"


@pytest.mark.parametrize(
    "question", ["What's the weather today?", "Tell me a joke", "capital of France"]
)
def test_genuinely_off_topic_is_still_refused(question: str) -> None:
    assert guide.intents(question, "learner")[0] == "off_topic"


@pytest.mark.parametrize("audience", ["learner", "employee", "manager"])
@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
def test_every_help_block_resolves_its_links_and_needs_no_attribution(
    audience: str, locale: str
) -> None:
    from app.features.assistant import service

    ctx = ctx_mod.Context(audience=audience)
    for topic in help_topics.TOPICS:
        text = guide.reply_for_intent(topic.id, ctx, locale)  # type: ignore[arg-type]
        _, rejected = service.to_parts(text, ctx)
        assert not rejected, (topic.id, audience, locale, rejected)
        assert service._meta([topic.id], ctx) is None
        # Fixed blocks never carry figures or catalogue entities.
        assert not re.search(r"\[\[(?:role|skill|course|sdg):", text)
