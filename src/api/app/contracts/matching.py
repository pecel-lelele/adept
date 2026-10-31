"""F4 Future-role matching (owner M2)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, ScenarioId
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


class ScoreImprovement(BaseModel):
    skill: str
    label: str
    score_gain: float = Field(ge=0, le=1)
    new_rank: int | None = Field(
        default=None,
        ge=1,
        description="Estimated rank after raising this skill and reranking all roles.",
    )
    course_id: str | None = None
    course_title: str | None = None
    course_url: str | None = None


class CriticalOccupationBadge(BaseModel):
    edition: str
    masco4d: str
    occupation_label: str
    matched_title: str
    source_page: int
    pdf_page: int
    meta: RecommendationMeta


class RoleMatch(BaseModel):
    role_id: str
    label: str
    score: float = Field(ge=0, le=1, description="Sum of weight * value over components.")
    rank: int | None = Field(default=None, ge=1)
    other_scenario: ScenarioId | None = None
    other_score: float | None = Field(default=None, ge=0, le=1)
    other_rank: int | None = Field(
        default=None,
        ge=1,
        description="Other-scenario rank for the same profile, snapshot and SDG weight.",
    )
    components: list[ScoreComponent]
    missing_skills: list[Skill]
    partial_skills: list[Skill]
    sdg_targets: list[SdgTarget]
    critical_occupation: CriticalOccupationBadge | None = None
    improvements: list[ScoreImprovement] = Field(default_factory=list)
    profile_note: Literal["add_skills"] | None = Field(
        default=None, description="A sparse-profile notice; translate the code for display."
    )
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


class MatchMeta(RecommendationMeta):
    available_snapshots: list[date] = Field(
        default_factory=list,
        description="Stored snapshot dates supplied by the trend source used for this ranking.",
    )


class MatchResponse(BaseModel):
    matches: list[RoleMatch]
    meta: MatchMeta
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
        0.0, description="Skill trend position (0-1, median-scaled log-tanh), earlier snapshot."
    )
    position_after: float = Field(
        0.0, description="Skill trend position (0-1, median-scaled log-tanh), later snapshot."
    )
    effect: float = Field(
        description=(
            "Score points this skill moved the role: change in trend position times "
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
