"""Prepared offline matching counterfactual harness; no autorun, printing or result logs.

Call check_matching_counterfactual with a synthetic Profile and fixed snapshot only after
the scoring changes are complete. Unit tests use a dummy query, not fairness evidence.
Temporary profile-read substitutions are confined to this standalone harness process.
Matching/scoring functions are never replaced, duplicated or edited by the default query.
"""

from collections.abc import Callable
from datetime import date
from unittest.mock import patch

from app.contracts.common import ScenarioId
from app.contracts.matching import MatchResponse
from app.contracts.profile import Profile
from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.features.matching import service as matching_service
from app.features.profile import service as profile_service

MatchingQuery = Callable[[CurrentUser, ScenarioId, date], MatchResponse]


def build_personas(base: Profile) -> tuple[Profile, ...]:
    """One baseline, three one-attribute swaps, and a combined synthetic swap."""
    return tuple(
        base.model_copy(deep=True, update={"age": age, "gender": gender, "background": background})
        for age, gender, background in (
            (22, "synthetic-female", "synthetic-background-a"),
            (41, "synthetic-female", "synthetic-background-a"),
            (22, "synthetic-male", "synthetic-background-a"),
            (22, "synthetic-female", "synthetic-background-b"),
            (60, "synthetic-nonbinary", "synthetic-background-c"),
        )
    )


def check_matching_counterfactual(
    base: Profile,
    snapshot_date: date,
    *,
    scenario: ScenarioId = "moderate",
    query: MatchingQuery | None = None,
) -> None:
    """Assert complete ranked matches are invariant to protected-attribute swaps.

    No profiles are saved. Read substitutions are restored even on failure. The default
    calls the production matching service API with a fixed snapshot, using only a local
    development/CSV fixture environment. Do not call this in a running application server.
    """
    if query is None:
        settings = get_settings()
        if settings.app_env != "development" or settings.m3_backend != "csv":
            raise ValueError("Counterfactual evaluation requires isolated development CSV fixtures")
        query = matching_service.list_matches
    user = CurrentUser(base.user_id, base.display_name, "learner")
    expected: list[dict[str, object]] | None = None
    for persona in build_personas(base):
        with (
            patch.object(profile_service, "has_profile", return_value=True),
            patch.object(profile_service, "get_my_profile", return_value=persona),
        ):
            response = query(user, scenario, snapshot_date)
        if not response.matches:
            raise AssertionError("Counterfactual evaluation requires nonempty ranked matches")
        if response.meta.snapshot_date != snapshot_date:
            raise AssertionError("Counterfactual snapshots must be identical")
        ranked = [match.model_dump(mode="json") for match in response.matches]
        if expected is None:
            expected = ranked
        elif ranked != expected:
            raise AssertionError("Matching output changed under a protected-attribute swap")
