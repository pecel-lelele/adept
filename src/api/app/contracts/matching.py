"""F4 Future-role matching (owner M2)."""

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta
from app.contracts.profile import Skill
from app.contracts.sdg import SdgTarget


class ScoreComponent(BaseModel):
    name: str = Field(examples=["skill_overlap", "trend_outlook", "interest_fit"])
    weight: float = Field(ge=0, le=1)
    value: float = Field(
        ge=0,
        le=1,
        description=(
            "Component value 0..1 as used in the total. When `provided` is false this is "
            "the neutral 0.5, not a measurement."
        ),
    )
    provided: bool = Field(
        default=True,
        description=(
            "False when the user did not give the data this component scores (e.g. no "
            "interests), so the UI can show 'not provided' without parsing the explanation."
        ),
    )
    explanation: str


class RoleMatch(BaseModel):
    role_id: str
    label: str
    score: float = Field(ge=0, le=1, description="Sum of weight * value over components.")
    components: list[ScoreComponent]
    missing_skills: list[Skill]
    partial_skills: list[Skill]
    sdg_targets: list[SdgTarget]
    trend_coverage: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description=(
            "Share of the role's skill importance that had a trend value in the snapshot; "
            "None for mock responses. Low coverage means many skills fell back to neutral."
        ),
    )
    data_provenance_note: str | None = Field(
        default=None,
        description="Trend provider's provenance disclosure, including any demo-fixture caveat.",
    )
    meta: RecommendationMeta


class MatchResponse(BaseModel):
    matches: list[RoleMatch]
    meta: RecommendationMeta
    data_provenance_note: str | None = Field(
        default=None,
        description="Trend provider's provenance disclosure, including any demo-fixture caveat.",
    )


class ReplayDriver(BaseModel):
    skill_id: str
    label: str
    velocity_before: float
    velocity_after: float
    position_before: float = Field(
        0.0, description="Percentile of the skill's velocity among all skills, earlier snapshot."
    )
    position_after: float = Field(
        0.0, description="Percentile of the skill's velocity among all skills, later snapshot."
    )
    effect: float = Field(
        description=(
            "Score points this skill moved the role: change in its percentile position times "
            "its share of the role's importance times the trend weight; > 0 pushed up."
        )
    )


class RoleMovement(BaseModel):
    role_id: str
    label: str
    rank_before: int = Field(ge=1)
    rank_after: int = Field(ge=1)
    score_before: float
    score_after: float
    drivers: list[ReplayDriver] = Field(
        description="The required skills whose trend moved this role most between the dates."
    )


class ReplayResponse(BaseModel):
    """What changed between two trend snapshots for this learner, and why."""

    scenario: str
    from_date: str
    to_date: str
    movements: list[RoleMovement]
    meta: RecommendationMeta
