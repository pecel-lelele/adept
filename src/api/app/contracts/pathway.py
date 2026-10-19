"""F5 Reskilling pathway (owner M3)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.sdg import SdgTarget

GapStatus = Literal["have", "partial", "missing"]
UnmetReason = Literal["no_catalogue_course", "over_budget", "catalogue_tops_out"]
CourseStatus = Literal["not_started", "in_progress", "completed"]


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
        default=0, ge=0, description="What the learner pays after HRD Corp claims."
    )
    budget_myr: float = Field(default=0, ge=0)
    within_budget: bool = True
    hrd_eligible: bool = False
    gaps: list[SkillGap] = Field(default_factory=list)
    unmet: list[UnmetSkill] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    snapshot_version: str = ""


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


class ProgressUpdate(BaseModel):
    role_id: str = Field(max_length=80)
    course_id: str = Field(max_length=120)
    status: CourseStatus


class Badge(BaseModel):
    id: str
    kind: Literal["skill", "milestone"]
    label: str
    earned_at: date
    evidence: Literal["self_reported"] = "self_reported"
    skill_id: str | None = None


class SkillProgress(BaseModel):
    skill_id: str
    label: str
    start_level: int = Field(ge=0, le=5)
    current_level: int = Field(ge=0, le=5)
    target_level: int = Field(ge=1, le=5)
    closed: bool


class Progress(BaseModel):
    role_id: str
    course_status: dict[str, CourseStatus]
    percent_complete: float = Field(ge=0, le=1, description="Share of planned hours completed.")
    skills: list[SkillProgress]
    gap_closed: int = Field(ge=0)
    gap_total: int = Field(ge=0)
    badges: list[Badge]
    pathway: Pathway = Field(description="The plan this progress is tracked against.")
    meta: RecommendationMeta
