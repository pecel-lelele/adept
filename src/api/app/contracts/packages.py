"""Comparable learning proposals; HR selects, members explicitly accept."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.common import RecommendationMeta, ScenarioId
from app.contracts.pathway import Pathway

PackageKind = Literal["free_first", "budget_capped", "broader"]


class PackageMember(BaseModel):
    user_id: str
    pathway: Pathway
    available_budget_myr: float = Field(ge=0)


class TeamPackage(BaseModel):
    kind: PackageKind
    token: str
    role_id: str
    role_label: str
    members: list[PackageMember]
    total_cost_myr: float = Field(ge=0)
    max_weeks: int = Field(ge=0)
    unmet_skills: int = Field(ge=0)
    within_member_budgets: bool
    meta: RecommendationMeta
    selected_at: datetime | None = None
    selected_by: str | None = None


class PackageOptions(BaseModel):
    packages: list[TeamPackage]


class PackageChoice(BaseModel):
    role_id: str = Field(max_length=80)
    member_ids: list[str] = Field(min_length=1, max_length=50)
    scenario: ScenarioId = "moderate"
    kind: PackageKind
    token: str = Field(min_length=64, max_length=64)


class AssignedPackage(BaseModel):
    token: str
    kind: PackageKind
    selected_at: datetime
    pathway: Pathway


class AcceptPackage(BaseModel):
    token: str = Field(min_length=64, max_length=64)


class PackageRoleProposal(AcceptPackage):
    proposed_role_id: str = Field(min_length=1, max_length=80)
