"""Live SDG sync (F6): UN SDG API → `sdg_goals`, `sdg_targets`; curated mappings → maps.

- Goals and targets: official wording from the UN Statistics Division SDG API, stamped with
  today's `retrieved_at`.
- Role/skill links: the curated, evidence-backed files in `src/data/seed/sdg/` are the source
  of truth; links are upserted (reason, strength, evidence) and links no longer in the files
  are removed, so a dropped mapping disappears from the app too.

Run on a schedule with:
    cd src/api && python -m app.features.sdg.sync
or trigger `POST /api/v1/sdg/sync` with the `X-Sync-Token` header.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import psycopg

from app.contracts.guardrails import SyncReport
from app.core import seed
from app.features.guardrails.datasync import SyncResult, run_logged
from app.features.sdg import sources

SOURCE = "UN Statistics Division SDG API + Adept SDG mapping"

_GOAL = """
INSERT INTO sdg_goals (id, title, short_title, source_url, retrieved_at)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title, short_title = EXCLUDED.short_title,
    source_url = EXCLUDED.source_url, retrieved_at = EXCLUDED.retrieved_at
"""
_TARGET = """
INSERT INTO sdg_targets (id, goal, label, source_url, retrieved_at) VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET goal = EXCLUDED.goal, label = EXCLUDED.label,
    source_url = EXCLUDED.source_url, retrieved_at = EXCLUDED.retrieved_at
"""
_MAP = """
INSERT INTO {table} ({key}, sdg_target_id, reason, strength, evidence_source, evidence_url,
    evidence_note) VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT ({key}, sdg_target_id) DO UPDATE SET reason = EXCLUDED.reason,
    strength = EXCLUDED.strength, evidence_source = EXCLUDED.evidence_source,
    evidence_url = EXCLUDED.evidence_url, evidence_note = EXCLUDED.evidence_note
"""
# Table and key names come from this fixed list only, never from input.
_MAPS = (("role_sdg_map", "role_id"), ("skill_sdg_map", "skill_id"))


def _sync_maps(conn: psycopg.Connection[tuple[object, ...]]) -> int:
    written = 0
    for table, key in _MAPS:
        rows = seed.rows("sdg", table)
        keep: list[tuple[str, str]] = []
        for r in rows:
            conn.execute(
                _MAP.format(table=table, key=key),
                (r[key], r["sdg_target_id"], r["reason"], r["strength"], r["evidence_source"],
                 r["evidence_url"], r["evidence_note"]),
            )  # fmt: skip
            keep.append((r[key], r["sdg_target_id"]))
        existing = conn.execute(f"SELECT {key}, sdg_target_id FROM {table}").fetchall()
        for entity, target in existing:
            if (entity, target) not in keep:
                conn.execute(
                    f"DELETE FROM {table} WHERE {key} = %s AND sdg_target_id = %s",
                    (entity, target),
                )
        written += len(rows)
    return written


def sync_sdg(payload: list[dict[str, Any]] | None = None, today: date | None = None) -> SyncReport:
    def job(conn: psycopg.Connection[tuple[object, ...]]) -> SyncResult:
        data = payload if payload is not None else sources.fetch()
        goals, targets = sources.parse(data)
        when = today or date.today()
        for g in goals:
            conn.execute(
                _GOAL,
                (g.id, g.title, g.short_title, sources.GOAL_PAGE.format(n=g.id), when),
            )
        for t in targets:
            conn.execute(_TARGET, (t.id, t.goal, t.label, sources.GOAL_PAGE.format(n=t.goal), when))
        links = _sync_maps(conn)
        detail = f"{len(goals)} goals, {len(targets)} targets, {links} curated links"
        return len(goals) + len(targets) + links, 0, detail

    return run_logged(SOURCE, job)


if __name__ == "__main__":
    report = sync_sdg()
    print(report.model_dump_json(indent=2))
    raise SystemExit(0 if report.status == "ok" else 1)
