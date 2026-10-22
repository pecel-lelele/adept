"""Local accounts (Core, M4): POST /auth/signup, POST /auth/login, GET /auth/me."""

from fastapi import APIRouter, status

from app.contracts.accounts import Account, LoginIn, SessionResponse, SignupIn
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


@router.get("/me")
def me(user: CurrentUserDep) -> Account:
    return service.me(user)
