"""Sign-up and sign-in for local accounts (Core, M4). Everything is stored in PostgreSQL."""

from __future__ import annotations

import re
import secrets

from app.contracts.accounts import Account, LoginIn, SessionResponse, SignupIn
from app.contracts.org import JoinOrgIn
from app.core import accounts
from app.core.auth import CurrentUser, user_from_account
from app.core.errors import AppError, UnauthorizedError
from app.core.security import session
from app.features.org import service as org_service
from app.features.profile import service as profile_service


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
        has_profile=account.kind == "learner" and profile_service.has_profile(account.id),
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
            org_service.join_org(user_from_account(account), JoinOrgIn(code=body.join_code or ""))
    except Exception:
        # Sign-up is all or nothing: never leave an account without the organisation it was
        # created for (its email would be taken and /org/setup has nothing to edit).
        accounts.delete(account.id)
        raise
    return _session(accounts.find_by_id(account.id) or account)


def login(body: LoginIn) -> SessionResponse:
    found = accounts.find_for_login(body.email)
    # Same message for unknown email and wrong password: no account enumeration.
    if found is None or not session.check_password(body.password, found[1]):
        raise UnauthorizedError("Email or password is incorrect.")
    return _session(found[0])


def me(user: CurrentUser) -> Account:
    account = accounts.find_by_id(user.id)
    if account is None:
        raise UnauthorizedError("Unknown account. Please sign in again.")
    return to_contract(account)
