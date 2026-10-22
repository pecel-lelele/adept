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


class MemberListResponse(BaseModel):
    members: list[Member]


class JoinOrgIn(BaseModel):
    """A signed-in learner joins an organisation with the code their manager shared."""

    code: str = Field(min_length=4, max_length=16)


class GapHeatmapCell(BaseModel):
    role_id: str
    skill_id: str
    gap: float = Field(ge=0, le=1, description="Share of members missing the skill.")


class GapHeatmapResponse(BaseModel):
    role_ids: list[str]
    role_labels: dict[str, str] = Field(default_factory=dict, description="role_id -> label")
    skills: list[Skill]
    cells: list[GapHeatmapCell]
    meta: RecommendationMeta


class GroupPlan(BaseModel):
    org_id: str
    target_role_id: str
    target_role_label: str = ""
    assigned_member_ids: list[str]
    steps: list[PathwayStep]
    total_weeks: int = Field(ge=0)
    meta: RecommendationMeta
