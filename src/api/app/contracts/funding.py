"""F7 employer learning budgets and completion-based expense claims (MYR)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl

from app.contracts.packages import TeamPackage
from app.contracts.pathway import Course

Money = Annotated[Decimal, Field(ge=0, le=1_000_000, max_digits=10, decimal_places=2)]
FundingStatus = Literal[
    "requested", "approved", "submitted", "payable", "paid", "rejected", "cancelled"
]


class MemberBudgetIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=120)
    amount_myr: Money


class FundingRequest(BaseModel):
    course_id: str = Field(min_length=1, max_length=120)
    role_id: str = Field(min_length=1, max_length=80)
    amount_myr: Money
    quote_url: HttpUrl


class FundingSubmission(BaseModel):
    revision: int = Field(ge=1)
    amount_myr: Money
    receipt_url: HttpUrl
    receipt_reference: str = Field(min_length=3, max_length=120)
    purchased_at: datetime


class FundingCompletion(BaseModel):
    revision: int = Field(ge=1)
    url: str = Field(min_length=12, max_length=500, pattern=r"^https://")


class FundingDecision(BaseModel):
    revision: int = Field(ge=1)
    action: Literal["approve", "reject", "cancel", "accept_claim", "mark_paid"]
    note: str = Field(default="", max_length=300)
    payment_reference: str = Field(default="", max_length=120)


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


class FundingState(BaseModel):
    budgets: dict[str, Money] = Field(default_factory=dict)
    claims: list[FundingClaim] = Field(default_factory=list)
    budget_events: list[FundingEvent] = Field(default_factory=list)
    packages: list[TeamPackage] = Field(default_factory=list)
