"""Adapter port for skills gap calculations (F4 Matching -> F5 Pathway).

Delegates to pathway.service.skills_gap(), with a pluggable interface
so tests can inject fakes without depending on the pathway service.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

GapFn = Callable[[Mapping[str, int], str], dict[str, list[str]]]


def _default_skills_gap(levels: Mapping[str, int], role_id: str) -> dict[str, list[str]]:
    from app.features.pathway import service as pathway_service

    return pathway_service.skills_gap(levels, role_id)


# Pluggable gap provider: default calls pathway.service.skills_gap.
fetch_skills_gap: GapFn = _default_skills_gap
