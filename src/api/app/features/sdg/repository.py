"""Data access for SDGs. Reads the seed CSVs (`src/data/seed/sdg`), the same rows `make seed`
loads into `sdg_goals`, `sdg_targets`, `role_sdg_map`, `skill_sdg_map` and `org_regions`."""

from __future__ import annotations

from datetime import date

from app.contracts.common import Source
from app.contracts.sdg import SdgEvidence, SdgLink, SdgStrength, SdgTarget
from app.core import refdata

AREA = "sdg"
UN_API_URL = "https://unstats.un.org/SDGAPI/v1/sdg/Goal/List"
MAPPING_URL = "https://github.com/pecel-lelele/adept/blob/main/src/data/seed/sdg/"
MAPPING_DATE = date(2026, 10, 20)


def un_source() -> Source:
    goals = refdata.rows(AREA, "sdg_goals", order_by_id=True)
    retrieved = date.fromisoformat(goals[0]["retrieved_at"]) if goals else MAPPING_DATE
    return Source(name="UN Statistics Division SDG API", url=UN_API_URL, retrieved_at=retrieved)


def mapping_source() -> Source:
    return Source(
        name="Adept SDG mapping (draft, pending review)",
        url=MAPPING_URL,
        retrieved_at=MAPPING_DATE,
    )


def goals() -> list[dict[str, str]]:
    return [dict(r) for r in refdata.rows(AREA, "sdg_goals", order_by_id=True)]


def targets() -> dict[str, SdgTarget]:
    return {
        r["id"]: SdgTarget(goal=int(r["goal"]), target=r["id"], label=r["label"])
        for r in refdata.rows(AREA, "sdg_targets")
    }


def short_titles() -> dict[int, str]:
    return {
        int(g["id"]): g["short_title"] for g in refdata.rows(AREA, "sdg_goals", order_by_id=True)
    }


EVIDENCE_CHECKED = date(2026, 10, 20)


def _evidence(row: dict[str, str]) -> SdgEvidence | None:
    url = row.get("evidence_url", "")
    if not url:
        return None
    return SdgEvidence(
        source=Source(name=row.get("evidence_source", ""), url=url, retrieved_at=EVIDENCE_CHECKED),
        note=row.get("evidence_note", ""),
    )


def _links(table: str, key: str, entity_id: str, via: str) -> list[SdgLink]:
    known = targets()
    out: list[SdgLink] = []
    for r in refdata.rows(AREA, table):
        if r[key] != entity_id:
            continue
        strength: SdgStrength = "direct" if r.get("strength") == "direct" else "enabling"
        out.append(
            SdgLink(
                target=known[r["sdg_target_id"]].model_copy(
                    update={
                        "reason": r["reason"],
                        "strength": strength,
                    }
                ),
                reason=r["reason"],
                strength=strength,
                via=f"{via}:{entity_id}",
                reviewed=bool(r.get("reviewed_by")),
                evidence=_evidence(r),
            )
        )
    return out


def role_links(role_id: str) -> list[SdgLink]:
    return _links("role_sdg_map", "role_id", role_id, "role")


def skill_links(skill_id: str) -> list[SdgLink]:
    return _links("skill_sdg_map", "skill_id", skill_id, "skill")


def mapped_role_ids() -> set[str]:
    return {r["role_id"] for r in refdata.rows(AREA, "role_sdg_map")}


def mapped_skill_ids() -> set[str]:
    return {r["skill_id"] for r in refdata.rows(AREA, "skill_sdg_map")}


def org_state(org_id: str) -> str | None:
    for r in refdata.rows(AREA, "org_regions"):
        if r["org_id"] == org_id:
            return r["state"]
    return None


def orgs_in_state(state: str) -> list[str]:
    return [r["org_id"] for r in refdata.rows(AREA, "org_regions") if r["state"] == state]


def states() -> list[str]:
    return sorted({r["state"] for r in refdata.rows(AREA, "org_regions")})
