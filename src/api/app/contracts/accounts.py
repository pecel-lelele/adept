"""Local accounts: sign-up, sign-in, session (Core, owner M4)."""

from typing import Literal

from pydantic import BaseModel, Field

from app.contracts.org import OrganizationIn

AccountKind = Literal["learner", "org_admin"]


class SignupIn(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    workspace: Literal["individual", "organisation"] = "individual"
    # Required for an organisation workspace: the organisation this manager sets up.
    organisation: OrganizationIn | None = None
    # Optional for an individual: join an organisation with the code its manager shared.
    join_code: str | None = Field(default=None, max_length=16)
    consent: bool = Field(description="Accepted the data-use and estimates notice.")


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Account(BaseModel):
    id: str
    display_name: str
    email: str | None
    kind: AccountKind
    org_id: str | None = None
    has_profile: bool = Field(description="False until the intake questionnaire is saved.")


class SessionResponse(BaseModel):
    token: str = Field(description="Signed session token; keep it in an httpOnly cookie.")
    account: Account
    next_path: str = Field(description="Where the web app should send the user next.")
