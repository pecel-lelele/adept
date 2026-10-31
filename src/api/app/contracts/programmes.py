"""Employer learning programmes (F7, owner M4): outcome first, personalised routes, agreements.

HR starts from a business objective, confirms the roles and capabilities that serve it, picks
the people, and sets the date, paid learning time, budgets and restrictions. Adept proposes a
personalised route per person from the catalogue (never invented courses), shows what it costs
and whether it fits the date, and HR sends it. Each person reviews a learning agreement and
accepts, declines (when optional) or asks for a change. A programme never replaces the
person's own personal plan.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, ScenarioId
from app.contracts.pathway import Pathway

Objective = Literal[
    "ai_adoption",
    "process_automation",
    "data_driven",
    "customer_experience",
    "cybersecurity",
    "sustainability_esg",
    "compliance_risk",
    "smart_manufacturing",
    "digital_health",
    "people_learning",
    "digital_marketing",
    "redeploy_at_risk",
]
Route = Literal["foundation", "applied", "advanced"]
DeliveryFormat = Literal["self_paced", "live_online", "in_person", "hybrid"]
AssignmentStatus = Literal["assigned", "accepted", "declined", "change_requested"]
ChangeReason = Literal[
    "already_have_skill",
    "pace",
    "language",
    "accessibility",
    "schedule",
    "upfront_cost",
    "target_role",
    "other",
]


class RoleTarget(BaseModel):
    role_id: str = Field(max_length=80)
    headcount: int = Field(ge=1, le=50, description="People the company wants in this role.")


class ProgrammeBriefIn(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    objectives: list[Objective] = Field(min_length=1, max_length=4)
    roles: list[RoleTarget] = Field(min_length=1, max_length=5)
    member_ids: list[str] = Field(min_length=1, max_length=50)
    target_date: date
    hours_per_week: float = Field(ge=1, le=20, description="Paid learning time during work.")
    budget_total_myr: float = Field(ge=0, le=5_000_000, description="Programme ceiling.")
    budget_per_member_myr: float = Field(ge=0, le=100_000, description="Individual limit.")
    mandatory: bool = False
    certificate_required: bool = Field(
        default=False, description="Only courses with a completion certificate at a known price."
    )
    hrd_claimable_only: bool = False
    formats: list[DeliveryFormat] = Field(
        default_factory=lambda: ["self_paced", "live_online", "in_person", "hybrid"], min_length=1
    )
    scenario: ScenarioId = "moderate"


class ObjectiveOption(BaseModel):
    id: Objective
    role_ids: list[str] = Field(description="Roles in the catalogue that serve this objective.")


class RoleReadiness(BaseModel):
    role_id: str
    label: str
    skills: list[str] = Field(description="Capabilities (skill ids) the role requires.")
    skill_labels: list[str]
    team_readiness: float = Field(
        ge=0, le=1, description="Average share of required skill levels members already hold."
    )
    ready_members: int = Field(ge=0, description="Members holding 70%+ of the requirement.")


class ProgrammeMember(BaseModel):
    user_id: str
    display_name: str


class ProgrammeOptions(BaseModel):
    objectives: list[ObjectiveOption]
    roles: list[RoleReadiness]
    members: list[ProgrammeMember]
    default_target_date: date
    meta: RecommendationMeta


class MemberRoute(BaseModel):
    user_id: str
    display_name: str
    role_id: str
    role_label: str
    route: Route
    readiness: float = Field(ge=0, le=1, description="Share of required levels already held.")
    pathway: Pathway
    weeks_needed: int = Field(ge=0)
    weeks_available: int = Field(ge=0)
    on_track: bool
    hours_per_week_needed: float = Field(
        ge=0, description="Weekly hours to finish the courses by the target date."
    )
    cost_myr: float = Field(ge=0)
    budget_myr: float = Field(ge=0, description="What the programme can spend on this person.")
    open_gaps: int = Field(ge=0, description="Required skills courses cannot fully close.")


class RoleAllocation(BaseModel):
    role_id: str
    role_label: str
    headcount: int
    assigned: int
    shortfall: int = Field(ge=0, description="Places with nobody assigned.")


class ProgrammePlan(BaseModel):
    brief: ProgrammeBriefIn
    token: str = Field(description="Changes when members, catalogue, prices or budgets change.")
    routes: list[MemberRoute]
    allocations: list[RoleAllocation]
    unassigned_member_ids: list[str] = Field(default_factory=list)
    total_cost_myr: float = Field(ge=0)
    within_programme_budget: bool
    members_on_track: int = Field(ge=0)
    notes: list[str] = Field(default_factory=list, description="How the plan was decided.")
    meta: RecommendationMeta


class ProgrammeSend(BaseModel):
    brief: ProgrammeBriefIn
    token: str = Field(min_length=64, max_length=64)


class Agreement(BaseModel):
    """What a person is shown before accepting a programme."""

    programme_id: str
    title: str
    objectives: list[Objective]
    role_id: str
    role_label: str
    route: Route
    readiness: float
    mandatory: bool
    target_date: date
    hours_per_week: float
    budget_myr: float = Field(description="What the employer has committed for this person.")
    cost_myr: float
    sent_at: datetime
    sent_by: str


class ProgrammeAssignment(BaseModel):
    agreement: Agreement
    user_id: str
    pathway: Pathway
    status: AssignmentStatus = "assigned"
    decided_at: datetime | None = None
    change_reason: ChangeReason | None = None
    note: str = Field(default="", max_length=500)
    proposed_role_id: str | None = None
    proposed_role_label: str | None = None


class ProgrammeRecord(BaseModel):
    id: str
    brief: ProgrammeBriefIn
    sent_at: datetime
    sent_by: str
    total_cost_myr: float


class ProgrammeStatus(BaseModel):
    """A sent programme as HR sees it: who accepted, declined or asked for changes."""

    record: ProgrammeRecord
    assignments: list[ProgrammeAssignment]
    accepted: int
    pending: int
    declined: int
    change_requested: int


class ProgrammeList(BaseModel):
    programmes: list[ProgrammeStatus]
    package_assignments: list[ProgrammeAssignment] = Field(default_factory=list)


class MyProgrammes(BaseModel):
    assignments: list[ProgrammeAssignment]
    role_labels: dict[str, str] = Field(default_factory=dict)


class AssignmentDecision(BaseModel):
    decision: Literal["accept", "decline", "request_change"]
    reason: ChangeReason | None = None
    note: str = Field(default="", max_length=500)
    proposed_role_id: str | None = Field(default=None, max_length=80)
    consent: bool = Field(
        default=False,
        description=(
            "Explicit consent to share current skill levels and pathway gaps for this programme."
        ),
    )
