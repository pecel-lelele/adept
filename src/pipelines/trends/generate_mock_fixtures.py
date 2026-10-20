"""Fixture generator for trend snapshots (repointed to export_fixtures_from_db).

Retired the legacy synthetic BASE_ITEMS generator to eliminate divergent fixture paths.
All mock fixtures (mock_trends_2026-10-13.json, mock_trends_2026-10-20.json, and
mock_trends.json) are now exported verbatim from genuine PostgreSQL trend_snapshots
rows produced by the arXiv cs.AI query API pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pipelines.trends.export_fixtures_from_db import main as export_main  # noqa: E402


def generate_all() -> None:
    export_main()


if __name__ == "__main__":
    generate_all()
