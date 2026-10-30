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
from typing import Any, TypeVar

import psycopg

from app.contracts.org import Member, MembershipRole, Organization
from app.core.db import connection
from app.core.logging import get_logger
from app.core.refdata import StorageUnavailableError, use_postgres

log = get_logger("app.org.repository")

T = TypeVar("T")
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
        return [
            member if member.skills_shared else member.model_copy(update={"current_role_id": None})
            for member in _members.get(org_id, [])
        ]
    rows = _db(
        "load the members",
        lambda c: c.execute(
            """
            SELECT u.id, u.display_name,
                   CASE WHEN m.share_skills THEN p.current_role_id ELSE NULL END AS current_role_id,
                   m.intake_status,
                   m.share_skills AS skills_shared
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


def membership_role(user_id: str, org_id: str) -> MembershipRole | None:
    """The person's current role in this organisation, or None. Read on every request made in
    an organisation workspace, so removal takes effect immediately."""
    if not use_postgres():
        if _managers.get(user_id) == org_id:
            return "manager"
        if any(m.id == user_id for m in _members.get(org_id, [])):
            return "member"
        from app.core import accounts

        account = accounts.find_by_id(user_id)
        if account and account.kind == "org_admin" and account.org_id == org_id:
            return "manager"
        return None
    row = _db(
        "check the membership",
        lambda c: c.execute(
            "SELECT role FROM memberships WHERE user_id = %s AND org_id = %s", (user_id, org_id)
        ).fetchone(),
    )
    return row["role"] if row else None


def memberships_of(user_id: str) -> list[tuple[Organization, MembershipRole, bool]]:
    """Every organisation this person belongs to: (organisation, role, skills shared)."""
    if not use_postgres():
        out: list[tuple[Organization, MembershipRole, bool]] = []
        for org_id, org in _orgs.items():
            role = membership_role(user_id, org_id)
            if role is None:
                continue
            member = next((m for m in _members.get(org_id, []) if m.id == user_id), None)
            out.append((org, role, bool(member and member.skills_shared)))
        return out
    rows = _db(
        "load your organisations",
        lambda c: c.execute(
            "SELECT o.id, o.type, o.name, o.industry, o.size, o.join_code, m.role, "
            "m.share_skills FROM memberships m JOIN organizations o ON o.id = m.org_id "
            "WHERE m.user_id = %s ORDER BY m.joined_at, o.id",
            (user_id,),
        ).fetchall(),
    )
    return [(Organization.model_validate(r), r["role"], bool(r["share_skills"])) for r in rows]


def managers_of(org_id: str) -> list[str]:
    """User ids of the organisation's managers and advisors."""
    if not use_postgres():
        from app.core import accounts

        found = {uid for uid, oid in _managers.items() if oid == org_id}
        found |= {
            a.id
            for a, _hash in accounts._memory.values()
            if a.kind == "org_admin" and a.org_id == org_id
        }
        return sorted(found)
    rows = _db(
        "load the managers",
        lambda c: c.execute(
            "SELECT user_id FROM memberships WHERE org_id = %s AND role <> 'member'", (org_id,)
        ).fetchall(),
    )
    return [str(r["user_id"]) for r in rows]


def set_share_skills(org_id: str, user_id: str, share: bool) -> bool:
    """A member turns skill sharing on or off for one organisation. False if not a member."""
    if use_postgres():
        return _db(
            "save your sharing choice",
            lambda c: (
                c.execute(
                    "UPDATE memberships SET share_skills = %s, "
                    "skills_shared_at = CASE WHEN %s THEN now() ELSE NULL END "
                    "WHERE org_id = %s AND user_id = %s AND role = 'member'",
                    (share, share, org_id, user_id),
                ).rowcount
                > 0
            ),
        )
    members = _members.get(org_id, [])
    for i, m in enumerate(members):
        if m.id == user_id:
            members[i] = m.model_copy(update={"skills_shared": share})
            return True
    return False


def is_current_manager(org_id: str, user_id: str) -> bool:
    """Money operations check current membership, even when a JWT or account cache is stale."""
    if not use_postgres():
        return membership_role(user_id, org_id) in ("manager", "advisor")
    return bool(
        _db(
            "check the current manager membership",
            lambda c: c.execute(
                "SELECT 1 FROM memberships WHERE org_id = %s AND user_id = %s "
                "AND role IN ('manager', 'advisor')",
                (org_id, user_id),
            ).fetchone(),
        )
    )


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
                "INSERT INTO memberships (user_id, org_id, role, intake_status, share_skills, "
                "skills_shared_at) VALUES (%s, %s, 'member', %s, %s, "
                "CASE WHEN %s THEN now() END) ON CONFLICT (user_id, org_id) DO NOTHING",
                (
                    member.id,
                    org_id,
                    member.intake_status,
                    member.skills_shared,
                    member.skills_shared,
                ),
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
