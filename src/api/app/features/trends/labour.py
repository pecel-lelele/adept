"""Serve stored DOSM observations; page requests never fetch an upstream dataset."""

import json

import psycopg

from app.contracts.labour import MalaysiaLabourContext
from app.core.db import connection
from app.core.refdata import use_postgres
from app.core.seed import SEED_DIR


def current() -> MalaysiaLabourContext:
    if use_postgres():
        try:
            with connection() as conn:
                row = conn.execute(
                    "SELECT payload FROM malaysia_labour_context "
                    "ORDER BY observed_month DESC LIMIT 1"
                ).fetchone()
            if row:
                value = MalaysiaLabourContext.model_validate(row["payload"])
                return value.model_copy(
                    update={
                        "meta": value.meta.model_copy(
                            update={"served_from": "db", "is_fallback": False}
                        )
                    }
                )
        except psycopg.Error:
            pass  # The versioned public export retains its real observation/retrieval dates.
    value = MalaysiaLabourContext.model_validate(
        json.loads((SEED_DIR / "trends/malaysia_labour.json").read_text(encoding="utf-8"))
    )
    return value.model_copy(
        update={
            "meta": value.meta.model_copy(update={"served_from": "fixture", "is_fallback": True})
        }
    )
