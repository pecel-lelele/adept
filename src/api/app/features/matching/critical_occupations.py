"""Historical MyCOL badges from reviewed stored role IDs; never a scoring input."""

import csv
import json
from datetime import date

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.matching import CriticalOccupationBadge
from app.core.config import REPO_ROOT

REFERENCE = REPO_ROOT / "docs" / "reference"


def badge_for_role(role_id: str, scenario: ScenarioId) -> CriticalOccupationBadge | None:
    """Join an exact catalogue ID to an explicitly reviewed title and source group.

    No label, substring, model, or MASCO-group inference is permitted. Callers pass an
    already resolved stored role. Unreviewed roles deliberately have no badge.
    """
    with (REFERENCE / "critical-occupation-roles.csv").open(encoding="utf-8", newline="") as f:
        mapping = next((r for r in csv.DictReader(f) if r["role_id"] == role_id), None)
    if mapping is None:
        return None
    with (REFERENCE / "critical-occupations.csv").open(encoding="utf-8", newline="") as f:
        occupation = next(r for r in csv.DictReader(f) if r["masco4d"] == mapping["masco4d"])
    provenance = json.loads(
        (REFERENCE / "critical-occupations.provenance.json").read_text(encoding="utf-8")
    )
    retrieved = date.fromisoformat(occupation["retrieved_at"])
    return CriticalOccupationBadge(
        edition=occupation["edition"],
        masco4d=occupation["masco4d"],
        occupation_label=occupation["occupation_label"],
        matched_title=mapping["matched_title"],
        source_page=int(mapping["source_page"]),
        pdf_page=int(mapping["pdf_page"]),
        meta=RecommendationMeta(
            sources=[
                Source(
                    name=f"TalentCorp MyCOL {occupation['edition']}",
                    url=f"{provenance['source_url']}#page={mapping['pdf_page']}",
                    retrieved_at=retrieved,
                )
            ],
            # Date of the frozen curated reference, not the trend snapshot or request.
            snapshot_date=retrieved,
            scenario=scenario,
            is_estimate=False,
        ),
    )
