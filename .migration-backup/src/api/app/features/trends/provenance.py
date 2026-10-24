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
        start = _as_date(stored.get("observed_from"))
        end = _as_date(stored.get("observed_to"))
        if start and end:
            return start, end
    return window_from_note(note)
