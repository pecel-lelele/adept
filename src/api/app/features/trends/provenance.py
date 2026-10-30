"""When a trend snapshot's evidence was actually observed (F2, handoff H09).

A snapshot has a date (when it was published in the app) and an observation window (the
period the source data measures). For the historical demo snapshots these differ: arXiv
windows from October 2024 are replayed as 2026 demo snapshots. The window is read from the
stored metadata when the pipeline recorded it, else from the provenance note, so the app can
always say which period was measured and never imply newer evidence than it has.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg import Connection


def lock_snapshot(conn: Connection, snapshot_date: date | str) -> None:
    """Serialize trend writers for a date, even before its metadata row exists.

    Called inside the writer's transaction by both seed import and publication.
    The TRND namespace is separate from other application advisory locks; the lock
    is released on commit/rollback. FOR UPDATE alone cannot lock an absent row.
    """
    day = date.fromisoformat(snapshot_date) if isinstance(snapshot_date, str) else snapshot_date
    conn.execute("SELECT pg_advisory_xact_lock(%s, %s)", (0x54524E44, day.toordinal()))


# "2024-10-13..2024-10-19" (the first range in a note is the window the snapshot measures).
_RANGE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*\.\.\s*(\d{4}-\d{2}-\d{2})")


def _as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def window_from_note(note: object) -> tuple[date | None, date | None]:
    if not isinstance(note, str) or not note:
        return None, None
    match = _RANGE.search(note)
    if not match:
        return None, None
    start, end = (date.fromisoformat(g) for g in match.groups())
    return (start, end) if start <= end else (end, start)


def observation_window(stored: object, note: object) -> tuple[date | None, date | None]:
    """Explicit ``observed_from`` / ``observed_to`` win; otherwise parse the note."""
    if isinstance(stored, Mapping):
        start = _as_date(stored.get("observation_window_start") or stored.get("observed_from"))
        end = _as_date(stored.get("observation_window_end") or stored.get("observed_to"))
        if start and end:
            return start, end
    return window_from_note(note)


PROVENANCE_FIELDS = (
    "is_replay",
    "observation_window_start",
    "observation_window_end",
    "retrieved_at",
    "retrieved_at_basis",
    "retrieval_evidence",
)


def provenance_values(stored: Mapping[str, object], note: str | None = None) -> dict[str, object]:
    """Validate provenance at each persistence boundary; never infer a fetch from a slot."""
    from app.contracts.common import TrendProvenance

    start, end = observation_window(stored, note)
    values = {key: stored[key] for key in PROVENANCE_FIELDS if key in stored}
    values.update(observation_window_start=start, observation_window_end=end)
    parsed = TrendProvenance.model_validate(values)
    return {key: getattr(parsed, key) for key in PROVENANCE_FIELDS}
