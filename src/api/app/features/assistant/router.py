"""Adi: authenticated, bounded requests for each person's workspace."""

import asyncio
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Annotated

from fastapi import APIRouter, Header

from app.contracts.assistant import AssistantIn, AssistantReply
from app.core.auth import get_current_user
from app.features.assistant import service

router = APIRouter(prefix="/assistant", tags=["assistant"])
# No unbounded queue of context reads after visitors have already received a timeout.
ANSWER_TIMEOUT_S = 24.0  # leaves time for the web proxy's 30 s deadline
_WORKERS = ThreadPoolExecutor(max_workers=4, thread_name_prefix="adi-answer")
_SLOTS = threading.BoundedSemaphore(4)


def _answer(
    body: AssistantIn,
    x_demo_user: str | None,
    authorization: str | None,
    x_workspace: str | None,
    deadline: float,
) -> AssistantReply:
    user = get_current_user(x_demo_user, authorization, x_workspace)
    return service.answer(user, body, deadline)


@router.post("/chat")
async def chat(
    body: AssistantIn,
    x_demo_user: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
    x_workspace: Annotated[str | None, Header(max_length=100)] = None,
) -> AssistantReply:
    """Ask Adi about your own workspace using checked application facts."""
    if not _SLOTS.acquire(blocking=False):
        return service.unavailable(None, body)
    slots = _SLOTS
    try:
        future: Future[AssistantReply] = _WORKERS.submit(
            _answer,
            body,
            x_demo_user,
            authorization,
            x_workspace,
            time.monotonic() + ANSWER_TIMEOUT_S - 0.5,
        )
    except BaseException:
        slots.release()
        raise
    future.add_done_callback(lambda _: slots.release())
    try:
        return await asyncio.wait_for(asyncio.wrap_future(future), ANSWER_TIMEOUT_S)
    except TimeoutError:
        # Running context reads retain their slot; they cannot trigger late paid model calls.
        return service.unavailable(None, body)
