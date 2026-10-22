"""Adi, the Adept assistant: POST /assistant/chat (signed in or not)."""

from typing import Annotated

from fastapi import APIRouter, Header

from app.contracts.assistant import AssistantIn, AssistantReply
from app.core.auth import CurrentUser, get_current_user
from app.core.errors import UnauthorizedError
from app.features.assistant import service

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _optional_user(x_demo_user: str | None, authorization: str | None) -> CurrentUser | None:
    """Visitors get answers from public figures; a bad or expired session is treated the same."""
    if not x_demo_user and not authorization:
        return None
    try:
        return get_current_user(x_demo_user, authorization)
    except UnauthorizedError:
        return None


@router.post("/chat")
def chat(
    body: AssistantIn,
    x_demo_user: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> AssistantReply:
    """Ask Adi. Answers come from your Adept data (or public figures) and are checked first."""
    return service.answer(_optional_user(x_demo_user, authorization), body)
