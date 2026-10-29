import pytest

from app.core.auth import CurrentUser
from app.features.assistant import context, guide, service
from app.features.trends import mocks
from app.features.trends import service as trends_service


@pytest.mark.parametrize("locale", ["en", "ms", "zh"])
def test_score_explanations_use_match_improvements_and_weighted_components(
    locale: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        trends_service,
        "get_snapshot",
        lambda snapshot_date, scenario: mocks.snapshot(scenario, snapshot_date),
    )
    ctx = context.build(CurrentUser("aisyah", "Synthetic learner", "learner"), "moderate")
    match = ctx.facts["matches"][0]
    assert match["improvements"]
    answer = guide.reply_for_intent("score_improvement", ctx, locale)
    assert f"{match['score'] * 100:.1f}" in answer
    for component in match["components"]:
        assert f"{component['weight'] * 100:g}% × {component['value'] * 100:.1f}%" in answer
    for item in match["improvements"][:3]:
        assert f"[[skill:{item['skill']}]]" in answer
        assert f"{item['score_gain'] * 100:.1f}" in answer
    assert service.to_parts(answer, ctx)[1] == []
