"""Account store for local sign-up / login (Core, M4).

memory (csv backend, tests) or PostgreSQL (`users`, `memberships`), like the other stores.
`find_by_id` runs on every authenticated request, so it is cached briefly.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace
from typing import Literal

import psycopg

from app.core.db import connection
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.refdata import StorageUnavailableError, use_postgres

log = get_logger("app.accounts")

AccountKind = Literal["learner", "org_admin"]


@dataclass(frozen=True)
class Account:
    id: str
    display_name: str
    email: str | None
    kind: AccountKind
    org_id: str | None = None


_lock = threading.Lock()
_memory: dict[str, tuple[Account, str | None]] = {}
_cache: dict[str, tuple[float, Account | None]] = {}
CACHE_TTL_S = 30.0


def reset() -> None:
    with _lock:
        _memory.clear()
        _cache.clear()


def forget(user_id: str) -> None:
    """Drop a cached account (after its membership or organisation changed)."""
    _cache.pop(user_id, None)


_SELECT = """
    SELECT u.id, u.display_name, u.email, u.kind, u.password_hash,
           (SELECT m.org_id FROM memberships m WHERE m.user_id = u.id
            ORDER BY (m.role = 'member'), m.joined_at LIMIT 1) AS org_id
    FROM users u
"""


def _row(row: dict[str, object]) -> tuple[Account, str | None]:
    kind = row["kind"] if row["kind"] in ("learner", "org_admin") else "learner"
    account = Account(
        id=str(row["id"]),
        display_name=str(row["display_name"]),
        email=str(row["email"]) if row["email"] else None,
        kind=kind,  # type: ignore[arg-type]
        org_id=str(row["org_id"]) if row["org_id"] else None,
    )
    return account, row["password_hash"]  # type: ignore[return-value]


def find_by_id(user_id: str) -> Account | None:
    hit = _cache.get(user_id)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
        return hit[1]
    if not use_postgres():
        found = _memory.get(user_id)
        return found[0] if found else None
    try:
        with connection() as conn:
            row = conn.execute(_SELECT + " WHERE u.id = %s", (user_id,)).fetchone()
    except psycopg.Error as exc:
        log.warning("account lookup failed: %s", exc)
        raise StorageUnavailableError("could not check your session") from exc
    account = _row(row)[0] if row else None
    _cache[user_id] = (time.monotonic(), account)
    return account


def find_for_login(email: str) -> tuple[Account, str | None] | None:
    email = email.strip().lower()
    if not use_postgres():
        return next(
            (v for v in _memory.values() if v[0].email and v[0].email.lower() == email), None
        )
    try:
        with connection() as conn:
            row = conn.execute(_SELECT + " WHERE lower(u.email) = %s", (email,)).fetchone()
    except psycopg.Error as exc:
        raise StorageUnavailableError("could not sign you in") from exc
    return _row(row) if row else None


def create(account: Account, password_hash: str) -> Account:
    if find_for_login(account.email or "") is not None:
        raise AppError(
            "An account with this email already exists. Sign in instead.",
            status_code=409,
            code="email_taken",
        )
    if use_postgres():
        try:
            with connection() as conn:
                conn.execute(
                    "INSERT INTO users (id, display_name, email, kind, is_synthetic, "
                    "password_hash) VALUES (%s, %s, %s, %s, false, %s)",
                    (account.id, account.display_name, account.email, account.kind,
                     password_hash),
                )  # fmt: skip
        except psycopg.errors.UniqueViolation as exc:
            raise AppError(
                "An account with this email already exists. Sign in instead.",
                status_code=409,
                code="email_taken",
            ) from exc
        except psycopg.Error as exc:
            raise StorageUnavailableError("could not create the account") from exc
    with _lock:
        _memory[account.id] = (account, password_hash)
    forget(account.id)
    return account


def set_org(user_id: str, org_id: str) -> None:
    """Record the user's organisation (memberships are written by the org repository)."""
    with _lock:
        found = _memory.get(user_id)
        if found:
            _memory[user_id] = (replace(found[0], org_id=org_id), found[1])
    forget(user_id)
