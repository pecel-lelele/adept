"""Atomic annual budgets; database failures never switch to volatile storage."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import RLock
from typing import Any, TypeVar

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from app.contracts.funding import FundingState
from app.core.db import connection, reuse_connection
from app.core.refdata import StorageUnavailableError, use_postgres

T = TypeVar("T")
_memory: dict[str, FundingState] = {}
_lock = RLock()


@contextmanager
def ledger_scope(conn: psycopg.Connection[Any], org_id: str) -> Iterator[None]:
    """Transaction-local ledger scope, restored for nested borrowers and pooled connections."""
    previous = conn.execute("SELECT current_setting('app.funding_org', true) AS scope").fetchone()
    before = previous["scope"] or ""
    conn.execute("SELECT set_config('app.funding_org', %s, true)", (org_id,))
    try:
        yield
    finally:
        if conn.info.transaction_status != TransactionStatus.INERROR:
            conn.execute("SELECT set_config('app.funding_org', %s, true)", (before,))


def snapshot(org_id: str) -> FundingState:
    """Read without a ledger write lock, and release the connection before callers do I/O."""
    if not use_postgres():
        with _lock:
            return _memory.get(org_id, FundingState()).model_copy(deep=True)
    try:
        with connection() as conn, ledger_scope(conn, org_id):
            row = conn.execute(
                "SELECT state FROM learning_funding WHERE org_id = %s",
                (org_id,),
            ).fetchone()
        return FundingState.model_validate(row["state"]) if row else FundingState()
    except psycopg.Error as exc:
        raise StorageUnavailableError("could not read the funding ledger") from exc


def transact(org_id: str, year: int, change: Callable[[FundingState], T]) -> T:
    if not use_postgres():
        with _lock:
            state = _memory.get(org_id, FundingState()).model_copy(deep=True)
            result = change(state)
            _memory[org_id] = state
            return result
    try:
        with (
            connection() as conn,
            conn.transaction(),
            reuse_connection(conn),
            ledger_scope(conn, org_id),
        ):
            conn.execute(
                "INSERT INTO learning_funding (org_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (org_id,),
            )
            row = conn.execute(
                "SELECT state FROM learning_funding WHERE org_id = %s FOR UPDATE",
                (org_id,),
            ).fetchone()
            if row is None:
                raise StorageUnavailableError("funding ledger is missing")
            state = FundingState.model_validate(row["state"])
            result = change(state)
            conn.execute(
                "UPDATE learning_funding SET state = %s WHERE org_id = %s",
                (Jsonb(state.model_dump(mode="json")), org_id),
            )
            return result
    except psycopg.Error as exc:
        raise StorageUnavailableError("could not save the funding ledger") from exc


def remove_member_records(state: FundingState, user_id: str) -> None:
    """Remove private assignments while preserving anonymised audit event counts/history."""
    state.budgets = {k: v for k, v in state.budgets.items() if k.split(":", 1)[-1] != user_id}
    state.claims = [c for c in state.claims if c.user_id != user_id]
    for event in state.budget_events:
        if event.actor_id == user_id or event.note.startswith(user_id + ":"):
            if event.actor_id == user_id:
                event.actor_id = "deleted-account"
            event.note = ""
    for package in state.packages:
        package.members = [m for m in package.members if m.user_id != user_id]
        if package.selected_by == user_id:
            package.selected_by = None
    for claim in state.claims:
        for event in claim.events:
            if event.actor_id == user_id:
                event.actor_id = "deleted-account"
                event.note = ""
    # Programme assignments and records (F7 programmes feature).
    state.assignments = [a for a in state.assignments if a.user_id != user_id]
    for assignment in state.assignments:
        if assignment.agreement.sent_by == user_id:
            assignment.agreement = assignment.agreement.model_copy(
                update={"sent_by": "deleted-account"}
            )
    for prog in state.programmes:
        if prog.sent_by == user_id:
            prog.sent_by = "deleted-account"
        if user_id in prog.brief.member_ids:
            prog.brief = prog.brief.model_copy(
                update={
                    "member_ids": [
                        "deleted-account" if mid == user_id else mid
                        for mid in prog.brief.member_ids
                    ]
                }
            )


def forget_user(user_id: str, conn: psycopg.Connection[Any] | None = None) -> None:
    """Purge embedded learning/receipt records in the account deletion transaction."""
    if conn is not None:
        # Account deletion visits each ledger explicitly; no wildcard RLS bypass is granted.
        for org in conn.execute("SELECT id FROM organizations ORDER BY id").fetchall():
            with ledger_scope(conn, org["id"]):
                row = conn.execute(
                    "SELECT state FROM learning_funding WHERE org_id = %s FOR UPDATE",
                    (org["id"],),
                ).fetchone()
                if row is not None:
                    state = FundingState.model_validate(row["state"])
                    remove_member_records(state, user_id)
                    conn.execute(
                        "UPDATE learning_funding SET state = %s WHERE org_id = %s",
                        (Jsonb(state.model_dump(mode="json")), org["id"]),
                    )
    else:
        with _lock:
            for state in _memory.values():
                remove_member_records(state, user_id)


def export_user(user_id: str) -> list[dict[str, object]]:
    if use_postgres():
        try:
            with connection() as conn:
                rows = []
                for org in conn.execute("SELECT id FROM organizations ORDER BY id").fetchall():
                    with ledger_scope(conn, org["id"]):
                        row = conn.execute(
                            "SELECT org_id, state FROM learning_funding WHERE org_id = %s",
                            (org["id"],),
                        ).fetchone()
                        if row is not None:
                            rows.append(row)
        except psycopg.Error as exc:
            raise StorageUnavailableError("could not export learning funding") from exc
        states = [(r["org_id"], FundingState.model_validate(r["state"])) for r in rows]
    else:
        with _lock:
            states = [(org, state.model_copy(deep=True)) for org, state in _memory.items()]
    result: list[dict[str, object]] = []
    for org_id, state in states:
        budgets = {k: str(v) for k, v in state.budgets.items() if k.split(":", 1)[-1] == user_id}
        claims = [c.model_dump(mode="json") for c in state.claims if c.user_id == user_id]
        assignments = [
            dict(
                token=p.token,
                kind=p.kind,
                selected_at=str(p.selected_at),
                pathway=m.pathway.model_dump(mode="json"),
            )
            for p in state.packages
            for m in p.members
            if m.user_id == user_id
        ]
        programme_assignments = [
            a.model_dump(mode="json") for a in state.assignments if a.user_id == user_id
        ]
        programmes_sent = [
            p.model_dump(mode="json") for p in state.programmes if p.sent_by == user_id
        ]
        if budgets or claims or assignments or programme_assignments or programmes_sent:
            result.append(
                dict(
                    org_id=org_id,
                    budgets=budgets,
                    claims=claims,
                    assignments=assignments,
                    programme_assignments=programme_assignments,
                    programmes_sent=programmes_sent,
                )
            )
    return result
