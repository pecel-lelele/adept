"""Sign-up and sign-in for local accounts (Core, M4). Everything is stored in PostgreSQL."""

from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime

from app.contracts.accounts import (
    Account,
    AccountExport,
    DeleteAccountIn,
    LoginIn,
    SessionResponse,
    SignupIn,
)
from app.contracts.org import JoinOrgIn
from app.core import accounts
from app.core.auth import CurrentUser, user_from_account
from app.core.errors import AppError, UnauthorizedError
from app.core.refdata import use_postgres
from app.core.security import session
from app.features.org import service as org_service
from app.features.profile import service as profile_service


def logout(user: CurrentUser) -> None:
    accounts.revoke_sessions(user.id)


def _new_user_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24] or "user"
    return f"u-{slug}-{secrets.token_hex(4)}"


def to_contract(account: accounts.Account) -> Account:
    return Account(
        id=account.id,
        display_name=account.display_name,
        email=account.email,
        kind=account.kind,
        org_id=account.org_id,
        has_profile=profile_service.has_profile(account.id),
    )


def next_path(account: accounts.Account) -> str:
    if account.kind == "org_admin":
        return "/org" if account.org_id else "/org/setup"
    return "/app" if profile_service.has_profile(account.id) else "/app/onboarding"


def _session(account: accounts.Account) -> SessionResponse:
    return SessionResponse(
        token=session.issue(account.id),
        account=to_contract(account),
        next_path=next_path(account),
    )


def signup(body: SignupIn) -> SessionResponse:
    if not body.consent:
        raise AppError("Please accept the notice to continue.", status_code=422, code="consent")
    org_mode = body.workspace == "organisation"
    if org_mode and body.organisation is None:
        raise AppError(
            "Tell us about your organisation to set up its workspace.",
            status_code=422,
            code="organisation_required",
        )
    join_org = None
    if not org_mode and body.join_code:
        from app.features.org import repository as org_repository

        join_org = org_repository.find_org_by_code(body.join_code)
        if join_org is None:
            raise AppError(
                "That join code does not match any organisation.",
                status_code=422,
                code="bad_join_code",
            )
        if not body.share_skills:
            raise AppError(
                "Explicit consent to share skill levels is required when joining.",
                status_code=422,
                code="sharing_consent_required",
            )
    name = " ".join(body.display_name.split())
    account = accounts.create(
        accounts.Account(
            id=_new_user_id(name),
            display_name=name,
            email=body.email.strip().lower(),
            kind="org_admin" if org_mode else "learner",
        ),
        session.hash_password(body.password),
    )
    try:
        if org_mode and body.organisation is not None:
            org_service.create_org(account, body.organisation)
        elif join_org is not None:
            org_service.join_org(
                user_from_account(account),
                JoinOrgIn(
                    code=body.join_code or "",
                    share_skills=body.share_skills,
                    consent=body.consent,
                ),
            )
    except Exception:
        # Sign-up is all or nothing: never leave an account without the organisation it was
        # created for (its email would be taken and /org/setup has nothing to edit).
        accounts.delete(account.id)
        raise
    return _session(accounts.find_by_id(account.id) or account)


# A real scrypt hash of a random password. Checking an unknown email against it costs the same
# time as a real check, so response time does not reveal which emails have accounts.
_DUMMY_HASH = session.hash_password(secrets.token_urlsafe(16))


def login(body: LoginIn) -> SessionResponse:
    found = accounts.find_for_login(body.email)
    # Same message and same work for unknown email and wrong password: no account enumeration.
    stored = found[1] if found is not None else _DUMMY_HASH
    if not session.check_password(body.password, stored) or found is None:
        raise UnauthorizedError("Email or password is incorrect.")
    return _session(found[0])


def export(user: CurrentUser) -> AccountExport:
    """Everything stored about the signed-in person, as one JSON document (PDPA access)."""
    from app.features.org import funding_store
    from app.features.pathway import repository as pathway_repository
    from app.features.pathway import service as pathway_service

    account = accounts.find_by_id(user.id)
    if account is None:
        raise UnauthorizedError("Unknown account. Please sign in again.")
    profile = (
        profile_service.get_my_profile(user).model_dump(mode="json")
        if profile_service.has_profile(user.id)
        else None
    )
    plan = pathway_service.get_saved_plan(user)
    store = pathway_repository.store()
    learning = [
        {
            "role_id": r.role_id,
            "course_id": r.course_id,
            "status": r.status,
            "course": r.course.model_dump(mode="json") if r.course else None,
            "evidence": r.evidence.model_dump(mode="json") if r.evidence else None,
        }
        for r in store.learning_records([user.id])
    ]
    # An empty list records nothing new: it only reads the badges already earned.
    badges = store.record_badges(user.id, [], datetime.now(UTC).date())
    return AccountExport(
        exported_at=datetime.now(UTC).isoformat(timespec="seconds"),
        account=to_contract(account),
        profile=profile,
        saved_plan=plan.model_dump(mode="json") if plan else None,
        plan_history=[p.model_dump(mode="json") for p in store.plan_history(user.id)],
        learning=learning,
        badges={badge: day.isoformat() for badge, day in badges.items()},
        learning_funding=funding_store.export_user(user.id),
    )


def _refuse_orphaning(user_id: str) -> None:
    """The last manager cannot delete their account while the organisation still has members,
    programmes or funding records: deleting it would silently erase their colleagues' work data.
    """
    from app.features.org import funding_store
    from app.features.org import repository as org_repository

    for org, role, _shared in org_repository.memberships_of(user_id):
        if role == "member" or org_repository.managers_of(org.id) != [user_id]:
            continue
        members = org_repository.list_members(org.id)
        state = funding_store.snapshot(org.id)
        if members or state.claims or state.programmes or state.budgets:
            raise AppError(
                f"You are the only manager of {org.name}, which still has "
                f"{len(members)} member(s) and its learning records. Remove the members first, "
                "or ask another manager to take over, then delete your account.",
                status_code=409,
                code="last_manager",
            )


def delete_account(user: CurrentUser, body: DeleteAccountIn) -> None:
    """Permanently delete the signed-in account after re-checking its password."""
    account = accounts.find_by_id(user.id)
    found = accounts.find_for_login(account.email or "") if account else None
    if found is None or not session.check_password(body.password, found[1]):
        raise UnauthorizedError("Password is incorrect.")
    _refuse_orphaning(user.id)
    accounts.delete(user.id, strict=True)
    if not use_postgres():
        from app.features.org import repository as org_repository

        org_repository.forget_user(user.id)


def me(user: CurrentUser) -> Account:
    account = accounts.find_by_id(user.id)
    if account is None:
        raise UnauthorizedError("Unknown account. Please sign in again.")
    return to_contract(account)
