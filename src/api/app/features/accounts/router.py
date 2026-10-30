"""Local accounts (Core, M4): sign-up, sign-in, the signed-in account, export and deletion."""

from fastapi import APIRouter, Response, status

from app.contracts.accounts import (
    Account,
    AccountExport,
    DeleteAccountIn,
    LoginIn,
    SessionResponse,
    SignupIn,
)
from app.core.auth import CurrentUserDep
from app.features.accounts import service

router = APIRouter(prefix="/auth", tags=["accounts"])


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn) -> SessionResponse:
    """Create an account (and, for an organisation workspace, the organisation)."""
    return service.signup(body)


@router.post("/login")
def login(body: LoginIn) -> SessionResponse:
    return service.login(body)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: CurrentUserDep) -> None:
    service.logout(user)


@router.get("/me")
def me(user: CurrentUserDep) -> Account:
    return service.me(user)


@router.get("/me/export")
def export_me(user: CurrentUserDep, response: Response) -> AccountExport:
    """Download everything stored about you (PDPA access request)."""
    response.headers["Content-Disposition"] = 'attachment; filename="adept-my-data.json"'
    return service.export(user)


@router.post("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(body: DeleteAccountIn, user: CurrentUserDep) -> None:
    """Permanently delete your account and everything linked to it (asks for your password)."""
    service.delete_account(user, body)
