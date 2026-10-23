"""Adapter port for role SDG badges (F4 Matching -> F6 SDG).

Delegates to sdg.service.role_badges(), with a pluggable interface
so tests can inject fakes without depending on the SDG service.
"""

from __future__ import annotations

from collections.abc import Callable

from app.contracts.sdg import SdgTarget

BadgeFn = Callable[[str], list[SdgTarget]]


def _default_role_badges(role_id: str) -> list[SdgTarget]:
    from app.features.sdg import service as sdg_service

    return sdg_service.role_badges(role_id)


# Pluggable badge provider: default calls sdg.service.role_badges.
fetch_role_badges: BadgeFn = _default_role_badges
