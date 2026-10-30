"""Adi: authenticated, bounded requests for each person's workspace."""

import asyncio
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Annotated

from fastapi import APIRouter, Header

from app.contracts.assistant import AssistantIn, AssistantReply
from app.core.auth import CurrentUser, get_current_user
from app.features.assistant import service

router = APIRouter(prefix="/assistant", tags=["assistant"])
# No unbounded queue of context reads after visitors have already received a timeout.
ANSWER_TIMEOUT_S = 24.0  # leaves time for the web proxy's 30 s deadline
_WORKERS = ThreadPoolExecutor(max_workers=4, thread_name_prefix="adi-answer")
_SLOTS = threading.BoundedSemaphore(4)
# At most one answer in flight per account, so one person cannot occupy every slot. An entry
# stays until its worker finishes, including after the caller has received a timeout reply.
_IN_FLIGHT: set[str] = set()
_IN_FLIGHT_LOCK = threading.Lock()


def _claim(user_id: str) -> bool:
    with _IN_FLIGHT_LOCK:
        if user_id in _IN_FLIGHT:
            return False
        _IN_FLIGHT.add(user_id)
        return True


def _release(user_id: str) -> None:
    with _IN_FLIGHT_LOCK:
        _IN_FLIGHT.discard(user_id)


def _answer(
    body: AssistantIn,
    x_demo_user: str | None,
    x_workspace: str | None,
    deadline: float,
    seen: list[CurrentUser],
) -> AssistantReply:
    user = get_current_user(x_demo_user=x_demo_user, x_workspace=x_workspace)
    seen.append(user)  # lets a timeout reply offer this person's own follow-up chips
    if not _claim(user.id):
        return service.unavailable(user, body, "busy")
    try:
        return service.answer(user, body, deadline)
    finally:
        _release(user.id)


@router.post("/chat")
async def chat(
    body: AssistantIn,
    x_demo_user: Annotated[str | None, Header()] = None,
    x_workspace: Annotated[str | None, Header(max_length=100)] = None,
) -> AssistantReply:
    """Ask Adi about your own workspace using checked application facts."""
    if not _SLOTS.acquire(blocking=False):
        return service.unavailable(None, body, "overloaded")
    slots = _SLOTS
    seen: list[CurrentUser] = []
    try:
        future: Future[AssistantReply] = _WORKERS.submit(
            _answer,
            body,
            x_demo_user,
            x_workspace,
            time.monotonic() + ANSWER_TIMEOUT_S - 0.5,
            seen,
        )
    except BaseException:
        slots.release()
        raise
    future.add_done_callback(lambda _: slots.release())
    try:
        return await asyncio.wait_for(asyncio.wrap_future(future), ANSWER_TIMEOUT_S)
    except TimeoutError:
        # Running context reads retain their slot; they cannot trigger late paid model calls.
        return service.unavailable(seen[0] if seen else None, body, "timeout")
