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


LearningStyle = Literal["video", "reading", "hands-on", "classroom", "mixed"]


class ProfileIn(BaseModel):
    segment: Segment
    interests: list[str] = Field(default_factory=list)
    hours_per_week: int = Field(ge=0, le=80)
    budget_myr: float = Field(ge=0)
    hrd_eligible: bool
    learning_style: LearningStyle = Field(default="mixed", description="Preferred way to learn.")


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


class SkillSuggestion(BaseModel):
    """A catalogue skill whose meaning is close to an unrecognised skills-list entry."""

    term: str = Field(description="The CV's own wording (one of `unmatched_terms`).")
    skill_id: str
    label: str
    similarity: float = Field(ge=-1, le=1, description="Cosine similarity of the embeddings.")
    runner_up: str = Field(default="", description="The next-closest skill, for context.")


class CvExtractionResult(BaseModel):
    skills: list[ExtractedSkill]
    unmatched_terms: list[str] = Field(
        default_factory=list,
        max_length=30,
        description=(
            "Up to 30 unrecognised entries from explicit skills lists, for transient human review. "
            "Not verified skills, not persisted or scored; prose may contain other missed skills."
        ),
    )
    suggestions: list[SkillSuggestion] = Field(
        default_factory=list,
        description=(
            "Catalogue skills close in meaning to some `unmatched_terms` (embedding cosine "
            "similarity). Proposals only: nothing is added unless the person chooses it."
        ),
    )
    truncated: bool = False
    meta: RecommendationMeta


class SkillOption(BaseModel):
    """One entry of the skill bank a learner picks from (taxonomy/skills.csv)."""

    id: str
    label: str
    group: str = Field(description="e.g. 'Emerging AI-native skill'; empty if ungrouped.")
    aliases: list[str] = Field(
        default_factory=list, description="Approved catalogue search aliases."
    )


class SkillCatalogueResponse(BaseModel):
    skills: list[SkillOption]
    interests: list[str] = Field(
        default_factory=list, description="Interest tags used by role matching (roles.csv)."
    )


class SkillResolutionRequest(BaseModel):
    query: str = Field(min_length=1, max_length=80, strict=True)


class SkillResolutionCandidate(BaseModel):
    skill_id: str
    label: str
    method: Literal["alias", "fuzzy", "semantic"]
    score: float = Field(ge=-1, le=1, description="Tier-specific similarity; not a probability.")


class SkillResolutionResponse(BaseModel):
    query: str
    candidates: list[SkillResolutionCandidate] = Field(max_length=3)
    meta: RecommendationMeta
