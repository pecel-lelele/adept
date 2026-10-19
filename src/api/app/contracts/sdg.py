"""F6 SDG mapping (owner M3)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta


class SdgTarget(BaseModel):
    goal: int = Field(ge=1, le=17)
    target: str = Field(examples=["4.4"])
    label: str


class SdgLink(BaseModel):
    target: SdgTarget
    reason: str


class EntitySdgLinks(BaseModel):
    entity_type: Literal["role", "skill"]
    entity_id: str
    links: list[SdgLink]
    meta: RecommendationMeta


class GoalSummary(BaseModel):
    goal: int = Field(ge=1, le=17)
    label: str
    link_count: int


class SdgContribution(BaseModel):
    goals_summary: list[GoalSummary]
    links: list[SdgLink]
    meta: RecommendationMeta
