"""Adi, the Adept assistant (Core, owner M4; guardrails F8).

Adi answers from the person's own Adept data (profile, matches, plan, trend snapshot) or, for
visitors, from the public platform figures. Every role, skill, course, SDG target or page it
mentions is a reference resolved from the catalogue, never free text from the model.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, ScenarioId

Locale = Literal["en", "ms", "zh"]
RefKind = Literal["role", "skill", "course", "sdg", "page"]


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class AssistantIn(BaseModel):
    messages: list[AssistantMessage] = Field(
        min_length=1,
        max_length=12,
        description="Recent turns, oldest first; the last is the question.",
    )
    page: str = Field(default="/", max_length=120, description="Route the person is on.")
    scenario: ScenarioId = "moderate"
    locale: Locale = "en"


class AnswerPart(BaseModel):
    """One piece of the answer: plain text, or a checked reference rendered as a link."""

    kind: Literal["text", "role", "skill", "course", "sdg", "page"]
    text: str
    ref_id: str | None = None
    href: str | None = None


class AssistantReply(BaseModel):
    parts: list[AnswerPart]
    suggestions: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Up to three server-authored follow-up questions; tapping one asks it.",
    )
    suggestion_ids: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Catalogue IDs of the follow-up questions, in the same order.",
    )
    used_llm: bool = Field(description="False when the deterministic guide answered.")
    provider: str
    model: str
    grounded_on: list[str] = Field(
        default_factory=list, description="Which of your data the answer could use."
    )
    unchecked_figures: list[str] = Field(
        default_factory=list,
        description="Numbers in the answer that do not appear in your data (shown as a caution).",
    )
    meta: RecommendationMeta | None = None
    workspace: str = Field(
        default="personal", description="Workspace answered in: 'personal' or an organisation id."
    )
    workspace_name: str = Field(default="", description="Organisation name; empty if personal.")
