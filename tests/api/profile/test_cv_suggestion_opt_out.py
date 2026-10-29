"""UI uploads skip provider work; API callers retain optional semantic suggestions."""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.features.profile import skill_match


@pytest.mark.parametrize("endpoint", ["profile", "preview"])
@pytest.mark.parametrize("include_suggestions", [None, "true", "false"])
def test_cv_semantic_suggestions_are_optional(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    include_suggestions: str | None,
) -> None:
    suggest = Mock(
        return_value=[skill_match.Suggestion("SyntheticTool", "excel", "Spreadsheet analysis", 0.9)]
    )
    monkeypatch.setattr(skill_match, "suggest", suggest)
    response = client.post(
        f"/api/v1/{endpoint}/cv",
        params={} if include_suggestions is None else {"include_suggestions": include_suggestions},
        data={"synthetic_consent": "true"},
        files={
            "file": ("synthetic.txt", b"Skills: SyntheticTool\n" + b"x" * 200_000, "text/plain")
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["skills"] == []
    assert result["truncated"] is True
    assert result["unmatched_terms"]
    if include_suggestions == "false":
        suggest.assert_not_called()
        assert result["suggestions"] == []
    else:
        suggest.assert_called_once()
        assert result["suggestions"][0]["skill_id"] == "excel"
