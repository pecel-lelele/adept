"""Produce two genuinely distinct dated snapshots from real arXiv query API windows.

Fetches/loads two independent time windows from arXiv cs.AI query API:
  Window 1 (2024-10-06 to 2024-10-12): assigned to baseline period 2026-W42
    (fetch_date: 2026-10-13).
  Window 2 (2024-10-13 to 2024-10-19): assigned to delta period 2026-W43
    (fetch_date: 2026-10-20).

Scores:
- Snapshot 2026-10-13: baseline window on Window 1 (t0=2026-W42, t1=2026-W42).
- Snapshot 2026-10-20: delta window comparing Window 1 to Window 2 (t0=2026-W42, t1=2026-W43).
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
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

CACHE_DIR = REPO_ROOT / "src" / "data" / "seed" / "arxiv_raw"
RATE_LIMIT_S = 3.5


def fetch_window_papers(
    w_start: str,
    w_end: str,
    t_start: str,
    t_end: str,
    max_results: int = 350,
) -> list[dict[str, str]]:
    """Fetch or load cached papers for a specific submittedDate window from arXiv."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{w_start}_{w_end}.json"
    if cache_file.exists():
        print(f"[arxiv-query] Loading cached window from {cache_file}")
        with cache_file.open(encoding="utf-8") as fh:
            return json.load(fh)

    query = f"cat:cs.AI AND submittedDate:[{t_start} TO {t_end}]"
    url = (
        f"http://export.arxiv.org/api/query?search_query="
        f"{urllib.parse.quote(query)}&start=0&max_results={max_results}"
    )
    print(f"[arxiv-query] Fetching {query} ...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "adept-trends-pipeline/1.0 (adept-hackathon; research)"},
    )
    time.sleep(RATE_LIMIT_S)
    with urllib.request.urlopen(req, timeout=45) as resp:
        root = ET.fromstring(resp.read())

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    papers: list[dict[str, str]] = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        id_el = entry.find("atom:id", ns)
        title = " ".join((title_el.text or "").split()) if title_el is not None else ""
        abstract = " ".join((summary_el.text or "").split()) if summary_el is not None else ""
        arxiv_id = (id_el.text or "").strip() if id_el is not None else ""
        if title or abstract:
            papers.append({"arxiv_id": arxiv_id, "title": title, "abstract": abstract})

    with cache_file.open("w", encoding="utf-8") as fh:
        json.dump(papers, fh, ensure_ascii=False, indent=2)
    print(f"[arxiv-query] Cached {len(papers)} papers -> {cache_file}")
    return papers


def run() -> None:
    db_url = get_settings().database_url
    skills = load_skills()
    skill_ids = [s[0] for s in skills]

    # Two genuinely different real date windows via arXiv Query API
    papers_w42 = fetch_window_papers(
        "2024-10-06",
        "2024-10-12",
        "202410060000",
        "202410122359",
        max_results=350,
    )
    papers_w43 = fetch_window_papers(
        "2024-10-13",
        "2024-10-19",
        "202410130000",
        "202410192359",
        max_results=350,
    )

    print(f"Window 1 (2026-10-13 / 2026-W42): {len(papers_w42)} papers")
    print(f"Window 2 (2026-10-20 / 2026-W43): {len(papers_w43)} papers")

    skill_vectors = load_skill_vectors(skill_ids, db_url)
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    print("\nCounting mentions for Window 1 (W42) ...")
    counts_w42 = count_mentions(papers_w42, skill_ids, skill_vectors, model)
    write_signal_rows(counts_w42, len(papers_w42), date(2026, 10, 13), db_url)

    print("\nCounting mentions for Window 2 (W43) ...")
    counts_w43 = count_mentions(papers_w43, skill_ids, skill_vectors, model)
    write_signal_rows(counts_w43, len(papers_w43), date(2026, 10, 20), db_url)

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
