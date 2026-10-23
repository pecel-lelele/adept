"""Pre-approval reserves funds; HR-confirmed completion enables a receipt claim.

Payment is an off-platform finance action, recorded explicitly by HR. Provider URL
reachability never authorizes payment. Receipt/quote links are never fetched by the API.
"""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.contracts.funding import (
    FundingBudget,
    FundingClaim,
    FundingCompletion,
    FundingDecision,
    FundingEvent,
    FundingLedger,
    FundingRequest,
    FundingState,
    FundingSubmission,
    MemberBudgetIn,
)
from app.contracts.pathway import CompletionEvidence
from app.core import accounts
from app.core.auth import CurrentUser
from app.core.db import connection
from app.core.errors import AppError, NotFoundError
from app.core.refdata import use_postgres
from app.features.org import funding_store, repository, service
from app.features.pathway import data, verification
from app.features.pathway import repository as pathway_repository

RESERVED = {"approved", "submitted", "payable"}


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


def _https(url: str) -> str:
    if not url.startswith("https://"):
        _deny("Use an HTTPS quote or receipt link.")
    return url


def _budget(state: FundingState, user_id: str, year: int) -> FundingBudget:
    claims = [c for c in state.claims if c.user_id == user_id and c.year == year]
    reserved = sum((c.approved_myr for c in claims if c.status in RESERVED), Decimal(0))
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


def request(user: CurrentUser, year: int, body: FundingRequest) -> FundingLedger:
    org_id = _scope(user)
    if user.kind != "learner":
        raise AppError("Only members request reimbursement.", status_code=403)
    if year != current_year():
        _deny("New requests use the current budget year.")
    course = data.course_index().get(body.course_id)
    if not course or body.role_id not in data.target_role_ids():
        raise NotFoundError("Unknown course or target role.")
    if course.format == "subscription" or course.price_basis != "per_course":
        _deny("Shared, subscription and group purchases require direct employer procurement.")
    if body.amount_myr <= 0:
        _deny("Reimbursement requires a positive quoted course or certificate price.")
    if course.cost_myr == 0 and course.price_status == "listed":
        _deny("This learning resource is free; there is no course fee to reimburse.")
    # The course must build a role skill or a prerequisite of one.
    skills = {r.skill_id for r in data.requirements(body.role_id)}
    pending = list(skills)
    prereqs = data.prerequisites()
    while pending:
        for pre in prereqs.get(pending.pop(), {}):
            if pre not in skills:
                skills.add(pre)
                pending.append(pre)
    if not skills.intersection(course.skill_ids):
        _deny("Choose a course connected to this target role's skills or prerequisites.")

    def change(state: FundingState) -> None:
        if any(
            c.user_id == user.id
            and c.course.id == course.id
            and c.status not in {"rejected", "cancelled"}
            for c in state.claims
        ):
            _deny("This course already has a request for this course.")
        state.claims.append(
            FundingClaim(
                year=year,
                id=uuid4().hex,
                user_id=user.id,
                role_id=body.role_id,
                course=course,
                requested_myr=body.amount_myr,
                quote_url=_https(str(body.quote_url)),
                requested_at=datetime.now(UTC),
                events=[FundingEvent(at=datetime.now(UTC), actor_id=user.id, action="requested")],
            )
        )

    funding_store.transact(org_id, year, change)
    return ledger(user, year)


def _claim(state: FundingState, claim_id: str, revision: int) -> FundingClaim:
    claim = next((c for c in state.claims if c.id == claim_id), None)
    if claim is None:
        raise NotFoundError("Request not found.")
    if claim.revision != revision:
        _deny("This request changed. Refresh before continuing.")
    return claim


def complete(
    user: CurrentUser,
    year: int,
    claim_id: str,
    body: FundingCompletion,
) -> FundingLedger:
    """Explicit member action tracks even an approved course absent from the algorithmic plan."""
    org_id = _scope(user)

    def checked(state: FundingState) -> FundingClaim:
        claim = _claim(state, claim_id, body.revision)
        if claim.year != year:
            raise NotFoundError("Request not found in this budget year.")
        if claim.user_id != user.id or user.kind != "learner":
            raise AppError("Only the member can submit their certificate.", status_code=403)
        if claim.status != "approved":
            _deny("Certificate submissions require an approved purchase request.")
        return claim

    snapshot = checked(funding_store.snapshot(org_id))
    # Only the slow external check runs before the final revision check. Progress and
    # evidence must not change when a concurrent submission or cancellation wins.
    course = snapshot.course.model_copy(
        update={
            "cost_myr": float(snapshot.approved_myr),
            "price_status": "listed",
            "price_note": "Member quote approved by HR; verify against the receipt.",
        }
    )
    link_status = verification.check_link(body.url, course, verification.probe)
    checked_at = datetime.now(UTC)
    _scope(user)

    def record(state: FundingState) -> None:
        claim = checked(state)
        # PostgreSQL repositories borrow this funding transaction's connection, so
        # progress, evidence and the claim commit or roll back together.
        pathway_repository.set_course_status(user.id, claim.role_id, course.id, "completed", course)
        pathway_repository.save_evidence(
            user.id,
            CompletionEvidence(
                role_id=claim.role_id,
                course_id=course.id,
                kind="certificate_link",
                url=body.url,
                link_status=link_status,
                link_checked_at=checked_at,
                submitted_at=datetime.now(UTC),
            ),
        )
        claim.certificate_url = body.url
        claim.revision += 1
        claim.events.append(
            FundingEvent(
                at=datetime.now(UTC),
                actor_id=user.id,
                action="certificate_submitted",
            )
        )

    funding_store.transact(org_id, year, record)
    return ledger(user, year)


def _completion(claim: FundingClaim, org_id: str) -> CompletionEvidence:
    if use_postgres():
        # Borrow the ledger transaction and keep evidence/progress stable until its commit.
        with connection() as conn:
            params = (claim.user_id, claim.role_id, claim.course.id)
            conn.execute(
                "SELECT 1 FROM course_progress WHERE user_id=%s AND role_id=%s "
                "AND course_id=%s FOR SHARE",
                params,
            )
            conn.execute(
                "SELECT 1 FROM course_evidence WHERE user_id=%s AND role_id=%s "
                "AND course_id=%s FOR SHARE",
                params,
            )
    rows = pathway_repository.store().learning_records([claim.user_id])
    row = next(
        (r for r in rows if r.role_id == claim.role_id and r.course_id == claim.course.id), None
    )
    ev = row.evidence if row else None
    if not row or row.status != "completed" or not ev or ev.kind != "org_confirmed" or not ev.url:
        _deny("HR must confirm the completion and certificate before a claim is payable.")
    assert ev is not None
    reviewer = accounts.find_by_id(ev.reviewed_by) if ev.reviewed_by else None
    if not reviewer or reviewer.kind != "org_admin" or reviewer.org_id != org_id:
        _deny("A manager of this organisation must confirm the completion evidence.")
    return ev


def submit(user: CurrentUser, year: int, claim_id: str, body: FundingSubmission) -> FundingLedger:
    org_id = _scope(user)

    def change(state: FundingState) -> None:
        claim = _claim(state, claim_id, body.revision)
        if claim.year != year:
            raise NotFoundError("Request not found in this budget year.")
        if claim.user_id != user.id or user.kind != "learner":
            raise AppError("Only the requesting member can submit receipts.", status_code=403)
        if claim.status != "approved":
            _deny("Get purchase approval before submitting a completion claim.")
        if body.amount_myr <= 0 or body.amount_myr > claim.approved_myr:
            _deny("Claim must be positive and cannot exceed the approved purchase cap.")
        if body.purchased_at.tzinfo is None:
            _deny("Purchase time must include a timezone.")
        if not claim.approved_at or not claim.approved_at <= body.purchased_at <= datetime.now(UTC):
            _deny("Only purchases made after approval and before today can be claimed.")
        reference = body.receipt_reference.strip().casefold()
        if len(reference) < 3:
            _deny("Give the receipt or invoice reference printed by the provider.")
        if any(
            c.id != claim.id
            and c.receipt_reference.casefold() == reference
            and c.status not in {"rejected", "cancelled"}
            for c in state.claims
        ):
            _deny("This receipt reference is already in use for this course.")
        evidence = _completion(claim, org_id)
        claim.evidence_submitted_at = evidence.submitted_at
        claim.certificate_url = evidence.url or ""
        claim.claimed_myr = body.amount_myr
        claim.receipt_url = _https(str(body.receipt_url))
        claim.receipt_reference = reference
        claim.purchased_at = body.purchased_at
        claim.status = "submitted"
        claim.revision += 1
        claim.events.append(
            FundingEvent(at=datetime.now(UTC), actor_id=user.id, action="submitted")
        )

    funding_store.transact(org_id, year, change)
    return ledger(user, year)


def decide(user: CurrentUser, year: int, claim_id: str, body: FundingDecision) -> FundingLedger:
    org_id = _scope(user)

    def change(state: FundingState) -> None:
        claim = _claim(state, claim_id, body.revision)
        if claim.year != year:
            raise NotFoundError("Request not found in this budget year.")
        if body.action == "cancel" and claim.user_id == user.id:
            if claim.status not in {"requested", "approved"}:
                _deny("Only an unsubmitted request can be cancelled.")
            claim.status = "cancelled"
        else:
            service.require_manager(user)
            if claim.user_id == user.id:
                raise AppError("Self-approval is not permitted.", status_code=403)
            if not any(m.id == claim.user_id for m in repository.list_members(org_id)):
                _deny("Member has left the organisation; arrange settlement through finance.")
            if body.action == "approve" and claim.status == "requested":
                if claim.requested_myr > _budget(state, claim.user_id, year).available_myr:
                    _deny("Insufficient unreserved member budget.")
                claim.approved_myr = claim.requested_myr
                claim.approved_at = datetime.now(UTC)
                claim.status = "approved"
            elif body.action == "reject" and claim.status in {
                "requested",
                "approved",
                "submitted",
                "payable",
            }:
                if not body.note.strip():
                    _deny("Give the member a reason for rejection.")
                claim.status = "rejected"
            elif body.action in {"accept_claim", "mark_paid"}:
                expected = "submitted" if body.action == "accept_claim" else "payable"
                if claim.status != expected:
                    _deny("Invalid claim transition.")
                evidence = _completion(claim, org_id)
                if (
                    evidence.submitted_at != claim.evidence_submitted_at
                    or evidence.url != claim.certificate_url
                ):
                    _deny("Completion evidence changed; reject and request a fresh claim.")
                if body.action == "mark_paid":
                    if not body.payment_reference.strip():
                        _deny("Record the external finance payment reference.")
                    claim.payment_reference = body.payment_reference.strip()
                claim.status = "payable" if body.action == "accept_claim" else "paid"
            else:
                _deny("Invalid claim transition.")
        claim.revision += 1
        claim.events.append(
            FundingEvent(at=datetime.now(UTC), actor_id=user.id, action=body.action, note=body.note)
        )

    funding_store.transact(org_id, year, change)
    return ledger(user, year)
