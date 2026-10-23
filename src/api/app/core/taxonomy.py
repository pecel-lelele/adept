"""Legacy IDs remain valid records; equivalent skills earn credit once."""

from collections.abc import Mapping

ALIASES = {"excel-basic": "excel", "robotic-process-automation": "rpa"}


def canonical(skill_id: str) -> str:
    return ALIASES.get(skill_id, skill_id)


def levels(values: Mapping[str, int]) -> dict[str, int]:
    out: dict[str, int] = {}
    for skill, level in values.items():
        key = canonical(skill)
        out[key] = max(out.get(key, 0), level)
    return out
