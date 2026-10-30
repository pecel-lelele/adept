"""Feature-local request/response models for profile (F1).

Shared models live in app/contracts/profile.py.
Feature-local models here cover:
  - Questionnaire intake request (M2-02): adds learning_style field not in shared Profile
  - Skill confirmation request (M2-03): user edits and submits the final skill list
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.profile import UserSkill

# ---------------------------------------------------------------------------
# M2-02: Questionnaire intake
# ---------------------------------------------------------------------------

LearningStyle = Literal["video", "reading", "hands-on", "classroom", "mixed"]


class QuestionnaireIn(BaseModel):
    """Full intake questionnaire payload (M2-02).

    Extends ProfileIn with learning_style which is captured during intake but
    not exposed in the public Profile contract to avoid scope creep in other
    features. Demographic fields (gender, age, race, ethnicity, etc.) are
    strictly rejected per the fairness whitelist.
    """

    model_config = ConfigDict(extra="forbid")

    segment: Literal["working", "graduate", "switcher"] = Field(
        description="Learner segment (working adult, fresh graduate, career switcher)."
    )
    interests: list[str] = Field(
        default_factory=list,
        description=(
            "Free-form interest tags. Only non-demographic interests are permitted; "
            "the matching engine's fairness whitelist rejects age/gender/race tags."
        ),
        examples=[["data", "finance", "AI"]],
    )
    hours_per_week: int = Field(
        ge=0,
        le=80,
        description="Hours per week available for learning or reskilling.",
    )
    learning_style: LearningStyle = Field(
        default="mixed",
        description="Preferred learning modality.",
    )
    budget_myr: float = Field(
        ge=0,
        description="Monthly training budget in Malaysian Ringgit.",
    )
    hrd_eligible: bool = Field(
        description=(
            "Whether the learner's employer is enrolled in HRD Corp "
            "(Human Resource Development Corporation), enabling subsidised training."
        )
    )


class QuestionnaireResponse(BaseModel):
    """Response after submitting the intake questionnaire."""

    user_id: str
    display_name: str
    segment: Literal["working", "graduate", "switcher"]
    interests: list[str]
    hours_per_week: int
    learning_style: LearningStyle
    budget_myr: float
    hrd_eligible: bool
    message: str = "Profile saved. Please confirm your skills."


# ---------------------------------------------------------------------------
# M2-03: Skill confirmation
# ---------------------------------------------------------------------------


class SkillEdit(BaseModel):
    """A single user-confirmed skill with their adjusted level."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(description="Must be a valid taxonomy skill ID.")
    level: int = Field(ge=1, le=5, description="Proficiency level 1 (novice) – 5 (expert).")
    source: Literal["cv", "form", "confirmed"] = "confirmed"


class SkillConfirmationIn(BaseModel):
    """Skill confirmation screen payload (M2-03).

    The user reviews extracted skills, optionally adds/removes/edits levels,
    and submits this payload to persist the final confirmed profile.
    """

    model_config = ConfigDict(extra="forbid")

    skills: list[SkillEdit] = Field(
        min_length=0,
        description="Final list of skills after user review. Replaces any previous skill list.",
    )


class SkillConfirmationResponse(BaseModel):
    """Response after the user confirms their skill list.

    Includes the normalised float representation that the scoring engine uses,
    so the frontend can preview the effective profile weights.
    """

    user_id: str
    confirmed_skills: list[UserSkill]
    normalised_skills: list[NormalisedSkill]
    message: str = "Skills confirmed and saved."


class NormalisedSkill(BaseModel):
    """Read-only view of a skill with its 0.0–1.0 normalised level.

    Formula: (level - 1) / 4.0 — same as matching/repository.py.
    """

    skill_id: str
    label: str
    level: int
    normalised_level: float = Field(
        description="Level mapped to 0.0 (novice) – 1.0 (expert), used by the scoring engine."
    )
