"""F2 AI-trend signal layer (owner M1)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta

EntityType = Literal["role", "skill"]
Direction = Literal["rising", "stable", "declining"]


class TrendSignal(BaseModel):
    entity_type: EntityType
    entity_id: str
    label: str
    direction: Direction
    growth_rate: float = Field(description="Year-on-year change in demand, e.g. 0.12 = +12%.")
    ai_exposure: float = Field(ge=0, le=1)
    automation_share: float = Field(ge=0, le=1)
    augmentation_share: float = Field(ge=0, le=1)


class RadarResponse(BaseModel):
    items: list[TrendSignal]
    meta: RecommendationMeta


class RoleTrendResponse(BaseModel):
    signal: TrendSignal
    meta: RecommendationMeta
