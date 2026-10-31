"""F7 Organisation mode (owner M4)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta
from app.contracts.pathway import PathwayStep
from app.contracts.profile import Skill

OrgType = Literal["company", "institution"]
IntakeStatus = Literal["invited", "in_progress", "complete"]


class Organization(BaseModel):
    id: str
    type: OrgType
    name: str
    industry: str
    size: int = Field(ge=0)
    join_code: str | None = Field(
        default=None, description="Code members enter to join. Shown to managers only."
    )


class OrganizationIn(BaseModel):
    """Editable organisation setup (PUT /org/me)."""

    type: OrgType
    name: str = Field(min_length=2, max_length=120)
    industry: str = Field(default="", max_length=120)
    size: int = Field(ge=0, le=1_000_000)


class Member(BaseModel):
    id: str
    display_name: str
    current_role_id: str | None
    intake_status: IntakeStatus
    skills_shared: bool = Field(
        default=False,
        description="The member chose to share their skill levels with this organisation. "
        "Only shared members count in team gaps and programme matching.",
    )


class MemberListResponse(BaseModel):
    members: list[Member]


class JoinOrgIn(BaseModel):
    """A signed-in learner joins an organisation with the code their manager shared."""

    code: str = Field(min_length=4, max_length=16)
    consent: bool = Field(
        default=False,
        description="Explicit consent to join this organisation. "
        "Required: a join without it is refused (M4-055).",
    )
    share_skills: bool = Field(
        strict=True,
        description="Explicit consent to share skill levels with this organisation's managers.",
    )


MembershipRole = Literal["member", "manager", "advisor"]


class Workspace(BaseModel):
    """A workspace the signed-in person can switch to."""

    id: str = Field(description="'personal' or an organisation id (sent as X-Workspace).")
    kind: Literal["personal", "org"]
    name: str = Field(description="Organisation name; empty for the personal workspace.")
    org_type: OrgType | None = None
    role: MembershipRole | None = None
    skills_shared: bool = False


class WorkspaceList(BaseModel):
    workspaces: list[Workspace]


class SharingIn(BaseModel):
    share_skills: bool


class GapHeatmapCell(BaseModel):
    role_id: str
    skill_id: str
    gap: float | None = Field(
        ge=0, le=1, description="Share below required level; null when suppressed."
    )
    suppressed: bool = False


class GapHeatmapResponse(BaseModel):
    role_ids: list[str]
    role_labels: dict[str, str] = Field(default_factory=dict, description="role_id -> label")
    skills: list[Skill]
    cells: list[GapHeatmapCell]
    cohort_size: int = Field(default=0, ge=0)
    min_cohort: int = Field(default=3, ge=1)
    role_suppressed: dict[str, bool] = Field(default_factory=dict)
    role_gaps: dict[str, float | None] = Field(
        default_factory=dict,
        description=(
            "role_id -> average gap over that role's required skills only. "
            "Suppressed rows are null. Unsuppressed cells for unrequired skills are 0 "
            "and must not be averaged."
        ),
    )
    meta: RecommendationMeta


class GroupPlan(BaseModel):
    org_id: str
    target_role_id: str
    target_role_label: str = ""
    assigned_member_ids: list[str]
    steps: list[PathwayStep]
    total_weeks: int = Field(ge=0)
    meta: RecommendationMeta
