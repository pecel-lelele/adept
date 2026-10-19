"""F4 Future-role matching (owner M2)."""

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta
from app.contracts.profile import Skill
from app.contracts.sdg import SdgTarget


class ScoreComponent(BaseModel):
    name: str = Field(examples=["skill_overlap", "trend_outlook", "interest_fit"])
    weight: float = Field(ge=0, le=1)
    value: float = Field(ge=0, le=1)
    explanation: str


class RoleMatch(BaseModel):
    role_id: str
    label: str
    score: float = Field(ge=0, le=1, description="Sum of weight * value over components.")
    components: list[ScoreComponent]
    missing_skills: list[Skill]
    partial_skills: list[Skill]
    sdg_targets: list[SdgTarget]
    meta: RecommendationMeta


class MatchResponse(BaseModel):
    matches: list[RoleMatch]
    meta: RecommendationMeta
