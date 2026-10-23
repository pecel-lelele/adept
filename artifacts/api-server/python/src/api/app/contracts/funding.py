"""F7 per-member training budgets HR sets for planning team packages (MYR)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.contracts.packages import TeamPackage
from app.contracts.pathway import Course
from app.contracts.programmes import ProgrammeAssignment, ProgrammeRecord

Money = Annotated[Decimal, Field(ge=0, le=1_000_000, max_digits=10, decimal_places=2)]
FundingStatus = Literal[
    "requested", "approved", "submitted", "payable", "paid", "rejected", "cancelled"
]


class MemberBudgetIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    amount_myr: Money


class FundingEvent(BaseModel):
    at: datetime
    actor_id: str
    action: str
    note: str = ""


class FundingClaim(BaseModel):
    year: int
    id: str
    user_id: str
    role_id: str
    course: Course
    requested_myr: Money
    approved_myr: Money = Decimal(0)
    claimed_myr: Money = Decimal(0)
    quote_url: str
    status: FundingStatus = "requested"
    revision: int = 1
    requested_at: datetime
    approved_at: datetime | None = None
    purchased_at: datetime | None = None
    receipt_url: str = ""
    receipt_reference: str = ""
    evidence_submitted_at: datetime | None = None
    certificate_url: str = ""
    payment_reference: str = ""
    events: list[FundingEvent] = Field(default_factory=list)


class FundingBudget(BaseModel):
    user_id: str
    amount_myr: Money
    reserved_myr: Money
    paid_myr: Money
    available_myr: Money


class FundingLedger(BaseModel):
    org_id: str
    year: int
    manager: bool
    budgets: list[FundingBudget]
    claims: list[FundingClaim]
    available_years: list[int] = Field(default_factory=list)


class FundingState(BaseModel):
    budgets: dict[str, Money] = Field(default_factory=dict)
    claims: list[FundingClaim] = Field(default_factory=list)
    budget_events: list[FundingEvent] = Field(default_factory=list)
    packages: list[TeamPackage] = Field(default_factory=list)
    # Employer programmes and each member's assignment and agreement status (F7).
    programmes: list[ProgrammeRecord] = Field(default_factory=list)
    assignments: list[ProgrammeAssignment] = Field(default_factory=list)
