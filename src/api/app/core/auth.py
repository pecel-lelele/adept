"""Authentication.

AUTH_MODE=demo (local accounts): people sign up and sign in through `/api/v1/auth/*`. The web
server keeps the signed session token in an httpOnly cookie and forwards it as `X-Demo-User`.
The API accepts only tokens it signed (`app.core.security.session`) for accounts stored in the
database; there are no built-in personas.
AUTH_MODE=supabase: `Authorization: Bearer <Supabase access token>`, verified with the
project JWT secret (`app.core.security.tokens`). Fails closed if no secret is configured.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastapi import Depends, Header

from app.core import accounts
from app.core.config import get_settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import session
from app.core.security.tokens import bearer_token, decode_token

UserKind = Literal["learner", "org_admin"]
_KINDS: tuple[UserKind, ...] = ("learner", "org_admin")
WorkspaceKind = Literal["personal", "org"]
PERSONAL_WORKSPACE = "personal"


@dataclass(frozen=True)
class CurrentUser:
    """The signed-in person *in the workspace this request was made in*.

    `X-Workspace: personal` gives a learner with no organisation, so organisation endpoints and
    data are unreachable. `X-Workspace: <organisation id>` requires a current membership; `kind`
    then follows that membership (manager/advisor -> org_admin, member -> learner). Without the
    header the account's own default applies (managers: their organisation; learners: personal,
    keeping their first organisation for older clients).
    """

    id: str
    display_name: str
    kind: UserKind
    org_id: str | None = None
    workspace: WorkspaceKind = "personal"

    @property
    def scope(self) -> str:
        """Owner of learning records written in this workspace."""
        return f"org:{self.org_id}" if self.workspace == "org" and self.org_id else "personal"


def user_from_claims(claims: dict[str, Any]) -> CurrentUser:
    """Map verified Supabase claims to a user. Only `app_metadata` may grant privilege."""
    app_meta = claims.get("app_metadata") or {}
    user_meta = claims.get("user_metadata") or {}
    raw_kind = app_meta.get("kind")
    kind: UserKind = raw_kind if raw_kind in _KINDS else "learner"
    org_id = app_meta.get("org_id")
    name = user_meta.get("display_name")
    return CurrentUser(
        id=str(claims["sub"]),
        display_name=str(name)[:80] if name else "Learner",
        kind=kind,
        org_id=str(org_id) if org_id else None,
        workspace="org" if kind == "org_admin" else "personal",
    )


def user_from_account(account: accounts.Account) -> CurrentUser:
    return CurrentUser(
        account.id,
        account.display_name,
        account.kind,
        account.org_id,
        "org" if account.kind == "org_admin" else "personal",
    )


def in_workspace(user: CurrentUser, workspace: str | None) -> CurrentUser:
    """Re-scope a user to the requested workspace, checking current membership each time."""
    if workspace is None or not workspace.strip():
        return user
    workspace = workspace.strip()
    if workspace == PERSONAL_WORKSPACE:
        return CurrentUser(user.id, user.display_name, "learner", None, "personal")
    from app.features.org import repository as org_repository

    role = org_repository.membership_role(user.id, workspace)
    if role is None:
        raise ForbiddenError("You are not a member of that organisation.")
    kind: UserKind = "learner" if role == "member" else "org_admin"
    return CurrentUser(user.id, user.display_name, kind, workspace, "org")


def _local_user(header: str | None) -> CurrentUser:
    settings = get_settings()
    value = header or settings.auth_default_user
    if not value:
        raise UnauthorizedError("Please sign in.")
    user_id = session.verify(value) if session.looks_like_token(value) else None
    if user_id is None and settings.auth_raw_user_ids:
        user_id = value  # test harness only
    if user_id is None:
        raise UnauthorizedError("Your session has expired. Please sign in again.")
    account = accounts.find_by_id(user_id)
    if account is None:
        raise UnauthorizedError("Unknown account. Please sign in again.")
    return user_from_account(account)


def get_current_user(
    x_demo_user: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
    x_workspace: Annotated[str | None, Header(max_length=100)] = None,
) -> CurrentUser:
    settings = get_settings()
    if settings.auth_mode == "demo":
        return in_workspace(_local_user(x_demo_user), x_workspace)
    claims = decode_token(
        bearer_token(authorization), settings.supabase_jwt_secret, settings.supabase_jwt_audience
    )
    return in_workspace(user_from_claims(claims), x_workspace)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
