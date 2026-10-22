"""F5 Reskilling pathway (owner M3)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.profile import Segment
from app.contracts.sdg import SdgTarget

GapStatus = Literal["have", "partial", "missing"]
UnmetReason = Literal[
    "no_catalogue_course", "over_budget", "catalogue_tops_out", "blocked_prerequisite"
]
CourseStatus = Literal["not_started", "in_progress", "completed"]
CourseFormat = Literal["self_paced", "live_online", "in_person", "hybrid", "subscription"]
CourseAudience = Literal["individual", "corporate", "both"]
PriceBasis = Literal["per_course", "per_user_year", "per_user_month", "per_group"]
ProviderType = Literal[
    "mooc", "university", "industry_body", "professional_body", "private_provider", "government"
]


class Course(BaseModel):
    id: str
    title: str
    provider: str
    url: str
    hours: float = Field(ge=0)
    cost_myr: float = Field(ge=0)
    hrd_claimable: bool
    verified_at: date
    skill_ids: list[str] = Field(default_factory=list)
    level: int = Field(
        default=2, ge=1, le=5, description="Skill level the course brings you to (estimate)."
    )
    hrd_note: str = ""
    duration_note: str = ""
    source: Source | None = None
    format: CourseFormat = "self_paced"
    audience: CourseAudience = "individual"
    price_basis: PriceBasis = "per_course"
    currency: str = Field(default="MYR", description="Currency of the provider's list price.")
    list_price: float | None = Field(default=None, ge=0, description="Price in `currency`.")
    provider_type: ProviderType = "private_provider"
    location: str = ""
    price_note: str = Field(default="", description="How cost_myr was derived (e.g. FX rate).")
    price_status: Literal["listed", "certificate_price_unknown"] = "listed"
    certificate_note: str = ""


class SkillGap(BaseModel):
    skill_id: str
    label: str
    current_level: int = Field(ge=0, le=5)
    required_level: int = Field(ge=1, le=5)
    importance: float = Field(ge=0)
    status: GapStatus


class PathwayStep(BaseModel):
    order: int = Field(ge=1)
    skill_id: str
    courses: list[Course]
    est_hours: float = Field(ge=0)
    week_start: int = Field(ge=1)
    week_end: int = Field(ge=1)
    reason: str
    skill_label: str = ""
    current_level: int = Field(default=0, ge=0, le=5)
    target_level: int = Field(default=1, ge=1, le=5)
    reaches_level: int = Field(default=1, ge=0, le=5)
    priority: float = Field(default=0, ge=0)
    prerequisites: list[str] = Field(default_factory=list)
    alternatives: list[Course] = Field(default_factory=list)
    out_of_pocket_myr: float = Field(default=0, ge=0)
    sdg_targets: list[SdgTarget] = Field(default_factory=list)
    member_ids: list[str] = Field(
        default_factory=list, description="Group plans: members who need this step."
    )


class UnmetSkill(BaseModel):
    skill_id: str
    label: str
    current_level: int
    required_level: int
    reason: UnmetReason
    detail: str


class Pathway(BaseModel):
    role_id: str
    steps: list[PathwayStep]
    total_weeks: int = Field(ge=0)
    meta: RecommendationMeta
    role_label: str = ""
    hours_per_week: float = Field(default=0, ge=0)
    total_hours: float = Field(default=0, ge=0)
    total_cost_myr: float = Field(default=0, ge=0, description="List price of all courses.")
    out_of_pocket_myr: float = Field(
        default=0,
        ge=0,
        description="Estimated list price before unquoted taxes/extras; "
        "HRD eligibility does not guarantee funding.",
    )
    budget_myr: float = Field(default=0, ge=0)
    within_budget: bool = True
    hrd_eligible: bool = False
    gaps: list[SkillGap] = Field(default_factory=list)
    unmet: list[UnmetSkill] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    snapshot_version: str = ""
    segment: Segment | None = Field(
        default=None,
        description="The learner's segment, for guidance text only; it never changes the plan.",
    )


class CatalogueResponse(BaseModel):
    courses: list[Course]
    meta: RecommendationMeta


class SavePlanIn(BaseModel):
    role_id: str = Field(max_length=80)
    scenario: ScenarioId = "moderate"


class SavedPlan(BaseModel):
    role_id: str
    scenario: ScenarioId
    snapshot_version: str
    saved_at: datetime
    pathway: Pathway


class PlanChange(BaseModel):
    kind: Literal["added", "removed", "reordered", "courses_changed"]
    skill_id: str
    detail: str


class ReplanStatus(BaseModel):
    saved: SavedPlan | None
    latest_snapshot_version: str
    needs_replan: bool
    changes: list[PlanChange]
    proposed: Pathway | None
    message: str
    meta: RecommendationMeta


TrendDirection = Literal["rising", "stable", "declining", "unknown"]


class RoleOption(BaseModel):
    """One candidate target role, so the learner can compare before choosing.

    Shows what the move would take (time, cost, gap) and the role's trend outlook. It does not
    rank roles (F4 matching does) and it never decides for the learner.
    """

    role_id: str
    role_label: str
    total_weeks: int = Field(ge=0)
    total_hours: float = Field(ge=0)
    out_of_pocket_myr: float = Field(ge=0)
    within_budget: bool
    skills_to_close: int = Field(ge=0, description="Required skills the learner lacks or is below.")
    unmet_skills: int = Field(ge=0, description="Skills no catalogue course can close.")
    trend_signal: float | None = Field(
        default=None,
        description="Importance-weighted trend velocity of the role's skills (estimate); "
        "None when the snapshot scores none of them.",
    )
    trend_direction: TrendDirection = "unknown"
    trend_coverage: float = Field(
        ge=0, le=1, description="Share of the role's skill importance that has trend data."
    )
    sdg_targets: list[SdgTarget] = Field(default_factory=list)
    is_saved_choice: bool = False


class RoleComparison(BaseModel):
    options: list[RoleOption]
    saved_role_id: str | None = None
    snapshot_version: str = ""
    available_snapshots: list[date] = Field(default_factory=list)
    meta: RecommendationMeta


class ProgressUpdate(BaseModel):
    role_id: str = Field(max_length=80)
    course_id: str = Field(max_length=120)
    status: CourseStatus


# Evidence ladder for a completed course, weakest first (KerjaCerdas proof-level idea).
EvidenceKind = Literal["self_reported", "certificate_link", "org_confirmed", "org_rejected"]
LinkStatus = Literal["not_submitted", "provider_verified", "unreachable", "not_provider_page"]


class CompletionEvidence(BaseModel):
    role_id: str
    course_id: str
    kind: EvidenceKind
    url: str | None = Field(default=None, description="Certificate or credential link.")
    link_status: LinkStatus = "not_submitted"
    link_checked_at: datetime | None = None
    submitted_at: datetime
    reviewed_by: str | None = Field(default=None, description="HR or advisor who reviewed it.")
    reviewed_at: datetime | None = None
    review_note: str = ""


class EvidenceSubmit(BaseModel):
    role_id: str = Field(max_length=80)
    course_id: str = Field(max_length=120)
    url: str = Field(min_length=12, max_length=500, pattern=r"^https://")


class ReviewDecision(BaseModel):
    user_id: str = Field(max_length=120)
    role_id: str = Field(max_length=80)
    course_id: str = Field(max_length=120)
    decision: Literal["confirm", "reject"]
    note: str = Field(default="", max_length=300)
    submitted_at: datetime | None = Field(
        description="`submitted_at` of the evidence the reviewer saw (null if none). The review "
        "is refused with 409 if the learner has changed the evidence since."
    )


class VerificationItem(BaseModel):
    user_id: str
    display_name: str
    role_id: str
    course: Course
    status: CourseStatus
    evidence: CompletionEvidence | None


class VerificationQueue(BaseModel):
    org_id: str
    pending: int = Field(ge=0, description="Completions not yet confirmed or rejected.")
    items: list[VerificationItem]


class Badge(BaseModel):
    id: str
    kind: Literal["skill", "milestone"]
    label: str
    earned_at: date
    evidence: Literal["self_reported", "certificate_link", "org_confirmed"] = Field(
        default="self_reported", description="Weakest evidence behind the badge."
    )
    skill_id: str | None = None
    skill_label: str = ""


class SkillProgress(BaseModel):
    skill_id: str
    label: str
    start_level: int = Field(ge=0, le=5)
    current_level: int = Field(ge=0, le=5)
    target_level: int = Field(ge=1, le=5)
    closed: bool


class CourseHistoryItem(BaseModel):
    role_id: str
    role_label: str
    course: Course
    status: CourseStatus
    evidence: CompletionEvidence | None = None


class Progress(BaseModel):
    role_id: str
    course_status: dict[str, CourseStatus]
    percent_complete: float = Field(ge=0, le=1, description="Share of planned hours completed.")
    skills: list[SkillProgress]
    gap_closed: int = Field(ge=0)
    gap_total: int = Field(ge=0)
    badges: list[Badge]
    history: list[CourseHistoryItem] = Field(
        default_factory=list,
        description="Completed courses across targets, independent of the remaining plan.",
    )
    evidence: dict[str, CompletionEvidence] = Field(
        default_factory=dict, description="Course id -> completion evidence."
    )
    pathway: Pathway = Field(description="The plan this progress is tracked against.")
    meta: RecommendationMeta
