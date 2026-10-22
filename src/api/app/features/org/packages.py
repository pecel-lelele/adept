"""F7 package previews reuse F5, never a separate course scoring formula."""

import hashlib
from dataclasses import replace
from datetime import UTC, datetime

from app.contracts.common import ScenarioId
from app.contracts.funding import FundingState
from app.contracts.packages import (
    AssignedPackage,
    PackageChoice,
    PackageMember,
    PackageOptions,
    TeamPackage,
)
from app.contracts.pathway import SavedPlan
from app.core.auth import CurrentUser
from app.core.errors import AppError, NotFoundError
from app.features.org import funding, funding_store, service
from app.features.pathway import data, repository, trend_port
from app.features.pathway import service as pathways


def options(
    user: CurrentUser, role_id: str | None, member_ids: list[str] | None, scenario: ScenarioId
) -> PackageOptions:
    org_id = funding.manager_scope(user)
    team = service.member_learners(org_id)
    ids = sorted(set(member_ids if member_ids is not None else team))
    if not ids or len(ids) > 50 or any(uid not in team for uid in ids):
        raise AppError("Select 1–50 current members with completed skill profiles.")
    team = {uid: team[uid] for uid in ids}
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


def accept(user: CurrentUser, token: str) -> SavedPlan:
    package = assigned(user)
    if package is None:
        raise NotFoundError("No assigned package.")
    if package.token != token:
        raise AppError("Your assignment changed. Refresh first.", status_code=409)
    # Selecting a proposal never overwrites a member's plan. This explicit action does.
    plan = package.pathway
    return repository.save_plan(
        user.id,
        SavedPlan(
            role_id=plan.role_id,
            scenario=plan.meta.scenario,
            snapshot_version=plan.snapshot_version,
            saved_at=datetime.now(UTC),
            pathway=plan,
        ),
    )
