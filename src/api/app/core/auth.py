"""Authentication.

AUTH_MODE=demo: no signup. The web app sets a cookie for a synthetic persona and
forwards it as the `X-Demo-User` header. AUTH_MODE=supabase is not implemented yet.
"""

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Header

from app.core.config import get_settings
from app.core.errors import AppError, UnauthorizedError

UserKind = Literal["learner", "org_admin"]


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


def get_current_user(
    x_demo_user: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    settings = get_settings()
    if settings.auth_mode == "demo":
        user = DEMO_USERS.get(x_demo_user or DEFAULT_DEMO_USER)
        if user is None:
            raise UnauthorizedError(f"Unknown demo user: {x_demo_user}")
        return user
    raise AppError("Supabase auth is not implemented yet", status_code=501, code="not_implemented")


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
