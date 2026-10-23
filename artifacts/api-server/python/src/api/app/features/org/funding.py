"""Per-member training budgets that HR sets for a year (MYR).

The budget is a planning input only: `/org/packages` uses it to build the budget-capped
package option. The organisation chooses and pays for training itself; members never pay
upfront or claim reimbursement through Adept (decision M4-062). Claim records stored by the
earlier reimbursement flow stay readable for export and deletion, but no new ones are made.
"""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from app.contracts.funding import (
    FundingBudget,
    FundingEvent,
    FundingLedger,
    FundingState,
    MemberBudgetIn,
)
from app.core.auth import CurrentUser
from app.core.errors import AppError, NotFoundError
from app.features.org import funding_store, repository, service


def current_year() -> int:
    """Employer budget years follow Malaysia's calendar, including the January boundary."""
    return datetime.now(timezone(timedelta(hours=8))).year


def _deny(message: str) -> None:
    raise AppError(message, status_code=409, code="funding_conflict")


def _scope(user: CurrentUser) -> str:
    org_id = user.org_id
    if not org_id:
        raise NotFoundError("Join an organisation to use its learning budget.")
    if user.kind == "org_admin":
        manager_scope(user)
    elif not any(m.id == user.id for m in repository.list_members(org_id)):
        raise AppError("Current organisation membership required.", status_code=403)
    return org_id


def manager_scope(user: CurrentUser) -> str:
    org_id = service.require_manager(user)
    if not repository.is_current_manager(org_id, user.id):
        raise AppError("Current organisation manager membership required.", status_code=403)
    return org_id


def _budget(state: FundingState, user_id: str, year: int) -> FundingBudget:
    claims = [c for c in state.claims if c.user_id == user_id and c.year == year]
    # Archived requests cannot be acted on, so their holds no longer reserve planning funds.
    reserved = Decimal(0)
    paid = sum((c.claimed_myr for c in claims if c.status == "paid"), Decimal(0))
    amount = state.budgets.get(f"{year}:{user_id}", Decimal(0))
    return FundingBudget(
        user_id=user_id,
        amount_myr=amount,
        reserved_myr=reserved,
        paid_myr=paid,
        available_myr=max(Decimal(0), amount - reserved - paid),
    )


def ledger(user: CurrentUser, year: int) -> FundingLedger:
    org_id = _scope(user)

    def read(state: FundingState) -> FundingLedger:
        ids = sorted(
            {k.split(":", 1)[1] for k in state.budgets}
            | {c.user_id for c in state.claims}
            | {m.id for m in repository.list_members(org_id)}
        )
        if user.kind != "org_admin":
            ids = [user.id]
        return FundingLedger(
            org_id=org_id,
            year=year,
            manager=user.kind == "org_admin",
            budgets=[_budget(state, uid, year) for uid in ids],
            claims=[
                c.model_copy(deep=True) for c in state.claims if c.user_id in ids and c.year == year
            ],
            available_years=sorted(
                {current_year(), year}
                | {
                    int(key.split(":", 1)[0])
                    for key in state.budgets
                    if key.split(":", 1)[-1] in ids
                }
                | {claim.year for claim in state.claims if claim.user_id in ids},
                reverse=True,
            ),
        )

    return read(funding_store.snapshot(org_id))


def budget(user: CurrentUser, year: int, body: MemberBudgetIn) -> FundingLedger:
    org_id = manager_scope(user)
    if not any(m.id == body.user_id for m in repository.list_members(org_id)):
        raise NotFoundError("Member not in this organisation.")

    def change(state: FundingState) -> None:
        current = _budget(state, body.user_id, year)
        if body.amount_myr < current.reserved_myr + current.paid_myr:
            _deny("Budget cannot be reduced below reserved and paid expenses.")
        state.budgets[f"{year}:{body.user_id}"] = body.amount_myr
        state.budget_events.append(
            FundingEvent(
                at=datetime.now(UTC),
                actor_id=user.id,
                action="set_budget",
                note=f"{body.user_id}: MYR {body.amount_myr} for {year}",
            )
        )

    funding_store.transact(org_id, year, change)
    return ledger(user, year)
