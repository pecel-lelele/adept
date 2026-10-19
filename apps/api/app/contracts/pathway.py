"""F5 Reskilling pathway (owner M3)."""

from datetime import date

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta


class Course(BaseModel):
    id: str
    title: str
    provider: str
    url: str
    hours: float = Field(ge=0)
    cost_myr: float = Field(ge=0)
    hrd_claimable: bool
    verified_at: date


class PathwayStep(BaseModel):
    order: int = Field(ge=1)
    skill_id: str
    courses: list[Course]
    est_hours: float = Field(ge=0)
    week_start: int = Field(ge=1)
    week_end: int = Field(ge=1)
    reason: str


class Pathway(BaseModel):
    role_id: str
    steps: list[PathwayStep]
    total_weeks: int = Field(ge=0)
    meta: RecommendationMeta
