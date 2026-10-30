"""Historical MyCOL badges from reviewed stored role IDs; never a scoring input."""

import csv
import json
from datetime import date
from functools import cache

from app.contracts.common import RecommendationMeta, ScenarioId, Source
from app.contracts.matching import CriticalOccupationBadge
from app.core.config import REPO_ROOT

REFERENCE = REPO_ROOT / "docs" / "reference"


@cache
def _reference_index() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], str]:
    """Read and index the frozen release assets once per worker process.

    New reference releases take effect on worker restart. Keep cached rows private;
    response models and scenario-specific metadata are constructed afresh below.
    """
    with (REFERENCE / "critical-occupation-roles.csv").open(encoding="utf-8", newline="") as f:
        mappings = {row["role_id"]: row for row in csv.DictReader(f)}
    with (REFERENCE / "critical-occupations.csv").open(encoding="utf-8", newline="") as f:
        occupations = {row["masco4d"]: row for row in csv.DictReader(f)}
    provenance = json.loads(
        (REFERENCE / "critical-occupations.provenance.json").read_text(encoding="utf-8")
    )
    return mappings, occupations, str(provenance["source_url"])


def badge_for_role(role_id: str, scenario: ScenarioId) -> CriticalOccupationBadge | None:
    """Join an exact catalogue ID to an explicitly reviewed title and source group.

    No label, substring, model, or MASCO-group inference is permitted. Callers pass an
    already resolved stored role. Unreviewed roles deliberately have no badge.
    """
    mappings, occupations, source_url = _reference_index()
    mapping = mappings.get(role_id)
    if mapping is None:
        return None
    occupation = occupations[mapping["masco4d"]]
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
                    url=f"{source_url}#page={mapping['pdf_page']}",
                    retrieved_at=retrieved,
                )
            ],
            # Date of the frozen curated reference, not the trend snapshot or request.
            snapshot_date=retrieved,
            scenario=scenario,
            is_estimate=False,
        ),
    )
