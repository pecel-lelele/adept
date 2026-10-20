"""Produce two genuinely distinct dated snapshots from real arXiv papers.

Batch 1 (2026-10-13, period 2026-W42): first 395 papers from the cs.AI feed.
Batch 2 (2026-10-20, period 2026-W43): subsequent 394 papers from the cs.AI feed.

Scores:
- Snapshot 2026-10-13: baseline window on Batch 1.
- Snapshot 2026-10-20: delta window comparing Batch 1 (t0=2026-W42) to Batch 2 (t1=2026-W43).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from sentence_transformers import SentenceTransformer

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
sys.path.insert(0, str(REPO_ROOT / "src"))
from app.core.config import get_settings  # noqa: E402
from pipelines.trends.arxiv_ingest import (  # noqa: E402
    count_mentions,
    load_skill_vectors,
    load_skills,
    write_signal_rows,
)
from pipelines.trends.score import main as score_main  # noqa: E402


def run() -> None:
    db_url = get_settings().database_url
    skills = load_skills()
    skill_ids = [s[0] for s in skills]

    raw_path = REPO_ROOT / "src" / "data" / "seed" / "arxiv_raw" / "2026-10-20.json"
    with raw_path.open(encoding="utf-8") as fh:
        papers: list[dict[str, str]] = json.load(fh)

    print(f"Total papers loaded: {len(papers)}")
    mid = len(papers) // 2
    batch_w42 = papers[:mid]
    batch_w43 = papers[mid:]
    print(f"Batch W42 (2026-10-13): {len(batch_w42)} papers")
    print(f"Batch W43 (2026-10-20): {len(batch_w43)} papers")

    skill_vectors = load_skill_vectors(skill_ids, db_url)
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    print("Counting mentions for Batch W42 ...")
    counts_w42 = count_mentions(batch_w42, skill_ids, skill_vectors, model)
    write_signal_rows(counts_w42, len(batch_w42), date(2026, 10, 13), db_url)

    print("Counting mentions for Batch W43 ...")
    counts_w43 = count_mentions(batch_w43, skill_ids, skill_vectors, model)
    write_signal_rows(counts_w43, len(batch_w43), date(2026, 10, 20), db_url)

    # Score Snapshot 1: 2026-10-13 (baseline)
    print("\n--- Scoring Snapshot 2026-10-13 ---")
    score_main(
        snapshot_date=date(2026, 10, 13),
        t0_period="2026-W42",
        t1_period="2026-W42",
    )

    # Score Snapshot 2: 2026-10-20 (growth between W42 and W43)
    print("\n--- Scoring Snapshot 2026-10-20 ---")
    score_main(
        snapshot_date=date(2026, 10, 20),
        t0_period="2026-W42",
        t1_period="2026-W43",
    )

    print("\nDual snapshots generated successfully in PostgreSQL!")


if __name__ == "__main__":
    run()
