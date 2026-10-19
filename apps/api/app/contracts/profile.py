"""F1 Skills profile intake (owner M2)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta

Segment = Literal["working", "graduate", "switcher"]
SkillSource = Literal["cv", "form", "confirmed"]


class Skill(BaseModel):
    id: str
    label: str


class UserSkill(BaseModel):
    skill_id: str
    level: int = Field(ge=1, le=5)
    source: SkillSource


class ProfileIn(BaseModel):
    segment: Segment
    interests: list[str] = Field(default_factory=list)
    hours_per_week: int = Field(ge=0, le=80)
    budget_myr: float = Field(ge=0)
    hrd_eligible: bool


class Profile(ProfileIn):
    user_id: str
    display_name: str
    current_role_id: str | None = None
    skills: list[UserSkill]


class SkillsUpdate(BaseModel):
    skills: list[UserSkill]


class ExtractedSkill(BaseModel):
    skill_id: str
    label: str
    level: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0, le=1)


class CvExtractionResult(BaseModel):
    skills: list[ExtractedSkill]
    meta: RecommendationMeta
