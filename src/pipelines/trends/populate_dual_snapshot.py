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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src" / "api"))
sys.path.insert(0, str(REPO_ROOT / "src"))
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
    raise SystemExit(
        "Retired: this bootstrap relabelled October 2024 arXiv windows as 2026 signals. "
        "Use the disclosed frozen historical fixtures for replay; run pipelines.trends.run "
        "only on genuinely dated source observations. No database rows were written."
    )


if __name__ == "__main__":
    run()
