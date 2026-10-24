"""F6 SDG mapping (owner M3)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, Source

SdgStrength = Literal["direct", "enabling"]
SdgScope = Literal["person", "organisation", "region"]


class SdgTarget(BaseModel):
    goal: int = Field(ge=1, le=17)
    target: str = Field(examples=["4.4"])
    label: str


class SdgEvidence(BaseModel):
    """The published source that justifies a link, and what in it does."""

    source: Source
    note: str


class SdgLink(BaseModel):
    target: SdgTarget
    reason: str
    strength: SdgStrength = Field(
        default="enabling",
        description="direct: the work itself advances the target; enabling: builds capacity.",
    )
    via: str = Field(default="", description="What the link comes from, e.g. 'skill:sql'.")
    reviewed: bool = Field(default=False, description="False = draft pending human review.")
    evidence: SdgEvidence | None = Field(
        default=None, description="Source justifying the link (UN metadata, ILO, UNESCO)."
    )


class EntitySdgLinks(BaseModel):
    entity_type: Literal["role", "skill"]
    entity_id: str
    links: list[SdgLink]
    meta: RecommendationMeta


class GoalSummary(BaseModel):
    goal: int = Field(ge=1, le=17)
    label: str
    link_count: int
    direct_count: int = 0
    enabling_count: int = 0
    is_focus: bool = Field(default=False, description="One of the domain focus goals.")
    contributors: int = Field(default=0, description="People whose plan links to this goal.")


class SdgContribution(BaseModel):
    goals_summary: list[GoalSummary]
    links: list[SdgLink]
    meta: RecommendationMeta
    scope: SdgScope = "person"
    scope_id: str = ""
    role_ids: list[str] = Field(default_factory=list)


class SdgGoal(BaseModel):
    goal: int = Field(ge=1, le=17)
    title: str
    short_title: str
    is_focus: bool
    targets: list[SdgTarget]
    source: Source


class SdgGoalListResponse(BaseModel):
    goals: list[SdgGoal]
    focus_goals: list[int]
    meta: RecommendationMeta


class SdgAlignment(BaseModel):
    role_id: str
    goals: list[int]
    score: float = Field(ge=0, le=1, description="Strength-weighted links to the chosen goals.")
    explanation: str
    links: list[SdgLink]
    meta: RecommendationMeta


class RegionListResponse(BaseModel):
    regions: list[str]
