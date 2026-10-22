"""Data access for organisations (F7).

Organisations, memberships and join codes live in PostgreSQL (`organizations`,
`memberships`, `users`; `M3_BACKEND=postgres`, the default). If the database is unreachable,
reads and writes fail with 503. `M3_BACKEND=csv` swaps in empty in-memory dicts for the
automated tests only; there are no built-in organisations.

Managers and advisors are memberships too, but only `role = 'member'` rows are listed.
A member's current role comes from their saved profile.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from typing import Any, Literal, TypeVar

import psycopg

from app.contracts.org import Member, Organization
from app.core.db import connection
from app.core.logging import get_logger
from app.core.refdata import StorageUnavailableError, use_postgres

log = get_logger("app.org.repository")

T = TypeVar("T")
MembershipRole = Literal["member", "manager", "advisor"]
_RANK = {"invited": 0, "in_progress": 1, "complete": 2}
# No 0/O/1/I so a code read aloud in a classroom is typed correctly.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Test-only memory store (M3_BACKEND=csv).
_orgs: dict[str, Organization] = {}
_members: dict[str, list[Member]] = {}
_managers: dict[str, str] = {}  # manager/advisor user id -> org id


def reset() -> None:
    _orgs.clear()
    _members.clear()
    _managers.clear()


def new_join_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


def _db(action: str, fn: Callable[[Any], T]) -> T:
    try:
        with connection() as conn:
            return fn(conn)
    except psycopg.Error as exc:
        log.warning("organisation storage failed (%s): %s", action, exc)
        raise StorageUnavailableError(f"could not {action}") from exc


_ORG_COLUMNS = "id, type, name, industry, size, join_code"


def get_org(org_id: str) -> Organization | None:
    if not use_postgres():
        return _orgs.get(org_id)
    row = _db(
        "load the organisation",
        lambda c: c.execute(
            f"SELECT {_ORG_COLUMNS} FROM organizations WHERE id = %s", (org_id,)
        ).fetchone(),
    )
    return Organization.model_validate(row) if row else None


def find_org_by_code(code: str) -> Organization | None:
    code = code.strip().upper()
    if not use_postgres():
        return next((o for o in _orgs.values() if o.join_code == code), None)
    row = _db(
        "check the join code",
        lambda c: c.execute(
            f"SELECT {_ORG_COLUMNS} FROM organizations WHERE join_code = %s", (code,)
        ).fetchone(),
    )
    return Organization.model_validate(row) if row else None


def create_org(org: Organization, owner_id: str, owner_role: MembershipRole) -> Organization:
    if use_postgres():

        def run(c: Any) -> None:
            with c.transaction():
                c.execute(
                    "INSERT INTO organizations (id, type, name, industry, size, join_code) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (org.id, org.type, org.name, org.industry, org.size, org.join_code),
                )
                c.execute(
                    "INSERT INTO memberships (user_id, org_id, role, intake_status) "
                    "VALUES (%s, %s, %s, 'complete')",
                    (owner_id, org.id, owner_role),
                )

        _db("create the organisation", run)
    else:
        _orgs[org.id] = org
        _members.setdefault(org.id, [])
        _managers[owner_id] = org.id
    return org


def list_members(org_id: str) -> list[Member]:
    if not use_postgres():
        return list(_members.get(org_id, []))
    rows = _db(
        "load the members",
        lambda c: c.execute(
            """
            SELECT u.id, u.display_name, p.current_role_id, m.intake_status
            FROM memberships m
            JOIN users u ON u.id = m.user_id
            LEFT JOIN profiles p ON p.user_id = m.user_id
            WHERE m.org_id = %s AND m.role = 'member'
            ORDER BY m.joined_at, u.id
            """,
            (org_id,),
        ).fetchall(),
    )
    return [Member.model_validate(r) for r in rows]


def update_org(org: Organization) -> Organization:
    if use_postgres():
        _db(
            "save the organisation",
            lambda c: c.execute(
                "UPDATE organizations SET type = %s, name = %s, industry = %s, size = %s "
                "WHERE id = %s",
                (org.type, org.name, org.industry, org.size, org.id),
            ),
        )
    else:
        _orgs[org.id] = org
    return org


def set_join_code(org_id: str, code: str) -> None:
    if use_postgres():
        _db(
            "rotate the join code",
            lambda c: c.execute(
                "UPDATE organizations SET join_code = %s WHERE id = %s", (code, org_id)
            ),
        )
    elif org_id in _orgs:
        _orgs[org_id] = _orgs[org_id].model_copy(update={"join_code": code})


def add_member(org_id: str, member: Member) -> Member:
    """Add an existing account as a member (joined with the organisation's code)."""
    if use_postgres():
        _db(
            "join the organisation",
            lambda c: c.execute(
                "INSERT INTO memberships (user_id, org_id, role, intake_status) "
                "VALUES (%s, %s, 'member', %s) ON CONFLICT (user_id, org_id) DO NOTHING",
                (member.id, org_id, member.intake_status),
            ),
        )
    else:
        members = _members.setdefault(org_id, [])
        if all(m.id != member.id for m in members):
            members.append(member)
    return member


def remove_member(org_id: str, member_id: str) -> bool:
    if use_postgres():
        return _db(
            "remove the member",
            lambda c: (
                c.execute(
                    "DELETE FROM memberships WHERE org_id = %s AND user_id = %s "
                    "AND role = 'member'",
                    (org_id, member_id),
                ).rowcount
                > 0
            ),
        )
    before = len(_members.get(org_id, []))
    _members[org_id] = [m for m in _members.get(org_id, []) if m.id != member_id]
    return len(_members[org_id]) < before


def forget_user(user_id: str) -> None:
    """Memory backend: drop a deleted account from every organisation (PostgreSQL cascades)."""
    for org_id in list(_members):
        _members[org_id] = [m for m in _members[org_id] if m.id != user_id]


def set_intake_status(user_id: str, status: str) -> None:
    """Move a learner's memberships forward (invited → in_progress → complete), never back.

    Best effort: the profile itself is already saved, so a failure here is only logged."""
    if use_postgres():
        try:
            with connection() as conn:
                conn.execute(
                    """
                    UPDATE memberships SET intake_status = %s
                    WHERE user_id = %s AND role = 'member' AND (
                        CASE intake_status WHEN 'invited' THEN 0
                                           WHEN 'in_progress' THEN 1 ELSE 2 END
                    ) < %s
                    """,
                    (status, user_id, _RANK[status]),
                )
        except psycopg.Error as exc:
            log.warning("could not update intake status for %s: %s", user_id, exc)
        return
    for members in _members.values():
        for i, m in enumerate(members):
            if m.id == user_id and _RANK[m.intake_status] < _RANK[status]:
                members[i] = m.model_copy(update={"intake_status": status})
