"""Read-only reference data for the pathway engine, from the seed CSVs.

- `courses/courses.csv` (F5, written by `pipelines.pathway`): the only courses we recommend.
- `pathway/skill_prerequisites.csv` (F5): the prerequisite graph.
- `taxonomy/*.csv` (F4, read-only here): roles, skills and role requirements.
- `trends/*.csv` (F2, read-only here): the legacy seed snapshot, used only as a fallback when
  M1's trend layer has no snapshot (see `trend_port.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from app.contracts.common import Source
from app.contracts.pathway import Course
from app.core import refdata, seed


@dataclass(frozen=True)
class Requirement:
    skill_id: str
    required_level: int
    importance: float


@dataclass(frozen=True)
class Snapshot:
    id: str
    version: str
    source: Source
    sources: tuple[Source, ...] = ()  # every source behind the snapshot (M1 has two)
    snapshot_date: date | None = None
    served_from: Literal["db", "fixture"] | None = None
    is_fallback: bool = False

    def all_sources(self) -> tuple[Source, ...]:
        return self.sources or (self.source,)


def catalogue() -> list[Course]:
    out: list[Course] = []
    # Retired courses (no longer listed by their provider) are never recommended.
    for r in refdata.rows("courses", "courses", non_retired_only=True, order_by_id=True):
        verified = date.fromisoformat(r["verified_at"])
        source_name = r.get("source_name") or r["provider"]
        out.append(
            Course(
                id=r["id"],
                title=r["title"],
                provider=r["provider"],
                url=r["url"],
                hours=float(r["hours"]),
                cost_myr=float(r["cost_myr"]),
                hrd_claimable=seed.as_bool(r["hrd_claimable"]),
                verified_at=verified,
                skill_ids=seed.pg_array(r["skill_ids"]),
                level=int(r.get("level") or 2),
                hrd_note=r.get("hrd_note", ""),
                duration_note=r.get("duration_note", ""),
                format=r.get("format") or "self_paced",  # type: ignore[arg-type]
                audience=r.get("audience") or "individual",  # type: ignore[arg-type]
                price_basis=r.get("price_basis") or "per_course",  # type: ignore[arg-type]
                currency=r.get("currency") or "MYR",
                list_price=float(r["list_price"]) if r.get("list_price") else None,
                provider_type=r.get("provider_type") or "private_provider",  # type: ignore[arg-type]
                location=r.get("location", ""),
                price_note=r.get("price_note", ""),
                price_status=(
                    "certificate_price_unknown"
                    if r["provider"].startswith("Coursera") and float(r["cost_myr"]) == 0
                    else "listed"
                ),
                certificate_note=(
                    "Free enrolment is not a free certificate. Confirm the paid certificate "
                    "price at checkout and request HR approval before purchase."
                    if r["provider"].startswith("Coursera") and float(r["cost_myr"]) == 0
                    else "Microsoft Learn modules award learning achievements, not professional "
                    "certification. Certification exams may have separate fees."
                    if r["provider"] == "Microsoft Learn"
                    else "Confirm certificate, taxes, eligibility and current price "
                    "with the provider."
                ),
                source=Source(
                    name=source_name, url=r.get("source_url") or r["url"], retrieved_at=verified
                ),
            )
        )
    return out


def course_index() -> dict[str, Course]:
    return {c.id: c for c in catalogue()}


def taxonomy_source() -> Source:
    return Source(
        name="O*NET 31.0 crosswalk + Adept curated role requirements (estimates)",
        url="https://github.com/pecel-lelele/adept/blob/main/"
        "src/data/seed/taxonomy/provenance.json",
        retrieved_at=date(2026, 10, 30),  # dated catalogue release in provenance.json
    )


def skill_labels() -> dict[str, str]:
    return {r["id"]: r["label"] for r in refdata.rows("taxonomy", "skills")}


def role_labels() -> dict[str, str]:
    return {r["id"]: r["label"] for r in refdata.rows("taxonomy", "roles")}


def requirements(role_id: str) -> list[Requirement]:
    return [
        Requirement(r["skill_id"], int(r["required_level"]), float(r["importance"]))
        for r in refdata.rows("taxonomy", "role_skills")
        if r["role_id"] == role_id
    ]


def target_role_ids() -> list[str]:
    """Roles a pathway can be built for (they have requirements), ordered by label."""
    labels = role_labels()
    candidates = {
        r["id"]
        for r in refdata.rows("taxonomy", "roles")
        if seed.as_bool(r.get("is_target", "true"))
    }
    ids = {r["role_id"] for r in refdata.rows("taxonomy", "role_skills")} & candidates
    return sorted((r for r in ids if r in labels), key=lambda r: labels[r])


def prerequisites() -> dict[str, dict[str, str]]:
    """skill_id -> {prerequisite_id: reason}."""
    out: dict[str, dict[str, str]] = {}
    for r in refdata.rows("pathway", "skill_prerequisites"):
        out.setdefault(r["skill_id"], {})[r["prerequisite_id"]] = r["reason"]
    return out


def snapshots() -> list[Snapshot]:
    """Trend snapshots, oldest first (by fetched_at)."""
    rows = sorted(seed.rows("trends", "snapshots"), key=lambda r: r["fetched_at"])
    out: list[Snapshot] = []
    for r in rows:
        fetched = datetime.fromisoformat(r["fetched_at"].replace("Z", "+00:00")).date()
        source = Source(name=r["source"], url=r.get("url") or "", retrieved_at=fetched)
        out.append(Snapshot(r["id"], r["version"], source))
    return out


def latest_snapshot() -> Snapshot | None:
    snaps = snapshots()
    return snaps[-1] if snaps else None


def skill_growth(snapshot_id: str) -> dict[str, float]:
    """skill_id -> year-on-year growth rate in that snapshot."""
    return {
        r["entity_id"]: float(r["growth_rate"])
        for r in seed.rows("trends", "trend_signals")
        if r["snapshot_id"] == snapshot_id and r["entity_type"] == "skill"
    }
