"""F7 package previews reuse F5, never a separate course scoring formula."""

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.contracts.common import ScenarioId
from app.contracts.funding import FundingState
from app.contracts.packages import (
    AssignedPackage,
    PackageChoice,
    PackageMember,
    PackageOptions,
    TeamPackage,
)
from app.contracts.programmes import Agreement, ProgrammeAssignment
from app.core.auth import CurrentUser
from app.core.errors import AppError, NotFoundError
from app.features.org import funding, funding_store, programmes, service
from app.features.pathway import data, trend_port
from app.features.pathway import service as pathways


def options(
    user: CurrentUser, role_id: str | None, member_ids: list[str] | None, scenario: ScenarioId
) -> PackageOptions:
    org_id = funding.manager_scope(user)
    team = service.member_learners(org_id)
    ids = sorted(set(member_ids if member_ids is not None else team))
    if len(ids) > 50 or any(uid not in team for uid in ids):
        raise AppError("Select 1–50 current members with completed skill profiles.")
    team = {uid: team[uid] for uid in ids}
    service.require_cohort(len(team))
    role = service.target_role(org_id, role_id, members=team)
    year = funding.current_year()
    budgets = {b.user_id: float(b.available_myr) for b in funding.ledger(user, year).budgets}
    catalogue = [
        c
        for c in data.catalogue()
        if c.price_status == "listed"
        and c.price_basis == "per_course"
        and c.format != "subscription"
    ]
    trend = trend_port.current(scenario)
    offers: list[TeamPackage] = []
    for kind in ("free_first", "budget_capped", "broader"):
        members = []
        for uid, learner in team.items():
            cap = 0 if kind == "free_first" else budgets.get(uid, 0)
            if kind == "broader":
                cap = 1_000_000
            plan = pathways.build_pathway(
                replace(learner, budget_myr=cap, hrd_eligible=False),
                role,
                scenario,
                trend=trend,
                catalogue=catalogue,
            )
            members.append(
                PackageMember(user_id=uid, pathway=plan, available_budget_myr=budgets.get(uid, 0))
            )
        offer = TeamPackage(
            kind=kind,
            token="",
            role_id=role,
            role_label=data.role_labels()[role],
            members=members,
            total_cost_myr=round(sum(m.pathway.total_cost_myr for m in members), 2),
            max_weeks=max(m.pathway.total_weeks for m in members),
            unmet_skills=sum(len(m.pathway.unmet) for m in members),
            within_member_budgets=all(
                m.pathway.total_cost_myr <= m.available_budget_myr for m in members
            ),
            meta=members[0].pathway.meta.model_copy(
                update={
                    "sources": list(
                        {
                            (source.name, source.url): source
                            for member in members
                            for source in member.pathway.meta.sources
                        }.values()
                    ),
                }
            ),
        )
        offer.token = hashlib.sha256(offer.model_dump_json().encode()).hexdigest()
        offers.append(offer)
    return PackageOptions(packages=offers)


def select(user: CurrentUser, body: PackageChoice) -> TeamPackage:
    org_id = funding.manager_scope(user)
    current = options(user, body.role_id, body.member_ids, body.scenario)
    offer = next(p for p in current.packages if p.kind == body.kind)
    if offer.token != body.token:
        raise AppError(
            "Catalogue, member skills or budgets changed. Compare the packages again.",
            status_code=409,
            code="stale_package",
        )
    offer.selected_at = datetime.now(UTC)
    offer.selected_by = user.id

    def save(state: FundingState) -> None:
        state.packages.append(offer)

    funding_store.transact(org_id, funding.current_year(), save)
    return offer


def assigned(user: CurrentUser) -> AssignedPackage | None:
    org_id = funding._scope(user)

    def read(state: FundingState) -> AssignedPackage | None:
        for package in reversed(state.packages):
            for member in package.members:
                if member.user_id == user.id and package.selected_at:
                    return AssignedPackage(
                        token=package.token,
                        kind=package.kind,
                        selected_at=package.selected_at,
                        pathway=member.pathway,
                    )
        return None

    return read(funding_store.snapshot(org_id))


def accept(user: CurrentUser, token: str) -> ProgrammeAssignment:
    return respond(user, token)


def respond(
    user: CurrentUser, token: str, proposed_role_id: str | None = None
) -> ProgrammeAssignment:
    """Accept the assigned team plan as a work programme.

    It never overwrites the person's personal plan, and it re-checks the route against today's
    skills, catalogue and budget instead of adopting a stale copy.
    """
    package = assigned(user)
    if package is None:
        raise NotFoundError("No assigned package.")
    if package.token != token:
        raise AppError("Your assignment changed. Refresh first.", status_code=409)
    org_id = funding._scope(user)
    stored = package.pathway
    proposed_label = (
        programmes.validate_role_proposal(proposed_role_id, stored.role_id)
        if proposed_role_id is not None
        else None
    )
    learner = service.member_learners(org_id, only=user.id).get(user.id)
    plan = stored
    budget = stored.total_cost_myr
    if learner is not None and proposed_role_id is None:
        budgets = {
            b.user_id: float(b.available_myr)
            for b in funding.ledger(user, funding.current_year()).budgets
        }
        budget = 0 if package.kind == "free_first" else budgets.get(user.id, 0)
        plan = pathways.build_pathway(
            replace(learner, budget_myr=budget, hrd_eligible=False),
            stored.role_id,
            stored.meta.scenario,
            catalogue=[
                c
                for c in data.catalogue()
                if c.price_status == "listed"
                and c.price_basis == "per_course"
                and c.format != "subscription"
            ],
        )
    now = datetime.now(UTC)
    weeks = max(1, plan.total_weeks)
    record_id = f"pkg-{token[:12]}"
    assignment = ProgrammeAssignment(
        user_id=user.id,
        pathway=plan,
        status="change_requested" if proposed_role_id else "accepted",
        change_reason="target_role" if proposed_role_id else None,
        proposed_role_id=proposed_role_id,
        proposed_role_label=proposed_label,
        decided_at=now,
        agreement=Agreement(
            programme_id=record_id,
            title=f"Team plan: {plan.role_label or stored.role_id}",
            objectives=[],
            role_id=plan.role_id,
            role_label=plan.role_label or data.role_labels().get(plan.role_id, plan.role_id),
            route=programmes.route_for(
                programmes.readiness(dict(learner.skill_levels), plan.role_id) if learner else 0
            ),
            readiness=programmes.readiness(dict(learner.skill_levels), plan.role_id)
            if learner
            else 0,
            mandatory=False,
            target_date=now.date() + timedelta(weeks=weeks),
            hours_per_week=plan.hours_per_week,
            budget_myr=float(budget),
            cost_myr=plan.total_cost_myr,
            sent_at=package.selected_at,
            sent_by="",
        ),
    )

    def save(state: FundingState) -> ProgrammeAssignment:
        latest = next(
            (p for p in reversed(state.packages) if any(m.user_id == user.id for m in p.members)),
            None,
        )
        if latest is None or latest.token != token:
            raise AppError("Your assignment changed. Refresh first.", status_code=409)
        existing = next(
            (
                a
                for a in state.assignments
                if a.user_id == user.id and a.agreement.programme_id == record_id
            ),
            None,
        )
        if proposed_role_id and existing is not None and existing.status == "accepted":
            # A proposal does not withdraw an accepted plan or its tracked progress.
            kept = existing.model_copy(
                update={
                    "change_reason": "target_role",
                    "proposed_role_id": proposed_role_id,
                    "proposed_role_label": proposed_label,
                    "decided_at": now,
                }
            )
            state.assignments[state.assignments.index(existing)] = kept
            return kept
        state.assignments = [
            a
            for a in state.assignments
            if not (a.user_id == user.id and a.agreement.programme_id == record_id)
        ]
        state.assignments.append(assignment)
        return assignment

    return funding_store.transact(org_id, funding.current_year(), save)
