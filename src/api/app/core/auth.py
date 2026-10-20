"""Authentication.

AUTH_MODE=demo: no signup. The web app sets a cookie for a synthetic persona and
forwards it as the `X-Demo-User` header.
AUTH_MODE=supabase: `Authorization: Bearer <Supabase access token>`, verified with the
project JWT secret (`app.core.security.tokens`). Fails closed if no secret is configured.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastapi import Depends, Header

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.security.tokens import bearer_token, decode_token

UserKind = Literal["learner", "org_admin"]
_KINDS: tuple[UserKind, ...] = ("learner", "org_admin")


@dataclass(frozen=True)
class CurrentUser:
    id: str
    display_name: str
    kind: UserKind
    org_id: str | None = None


# Synthetic personas only (docs/PROJECT_CONTEXT.md §11.5).
DEMO_USERS: dict[str, CurrentUser] = {
    "aisyah": CurrentUser("aisyah", "Aisyah", "learner", "org-demo-bank"),
    "weijie": CurrentUser("weijie", "Wei Jie", "learner"),
    "ravi": CurrentUser("ravi", "Ravi", "learner"),
    "demo-company": CurrentUser("demo-company", "Demo Bank HR", "org_admin", "org-demo-bank"),
    "demo-institution": CurrentUser(
        "demo-institution", "Demo Polytechnic Career Centre", "org_admin", "org-demo-poly"
    ),
}
DEFAULT_DEMO_USER = "aisyah"


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
    )


def get_current_user(
    x_demo_user: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    settings = get_settings()
    if settings.auth_mode == "demo":
        user = DEMO_USERS.get(x_demo_user or DEFAULT_DEMO_USER)
        if user is None:
            raise UnauthorizedError(f"Unknown demo user: {x_demo_user}")
        return user
    claims = decode_token(
        bearer_token(authorization), settings.supabase_jwt_secret, settings.supabase_jwt_audience
    )
    return user_from_claims(claims)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
