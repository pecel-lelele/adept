"""Served velocities share the pipeline's +/-2 bound, so Fast >= Moderate when rising."""

import pytest

from app.features.trends import mocks
from pipelines.trends.score import V_CLAMP_MAX, V_CLAMP_MIN


@pytest.mark.parametrize("snapshot_date", mocks.AVAILABLE_MOCK_DATES)
def test_fast_is_not_weaker_than_moderate_for_rising_skills(snapshot_date) -> None:
    items = mocks.snapshot("moderate", snapshot_date).items
    assert items
    for item in items:
        assert V_CLAMP_MIN <= item.velocity_moderate <= V_CLAMP_MAX
        assert V_CLAMP_MIN <= item.velocity_fast <= V_CLAMP_MAX
        if item.velocity_moderate > 0:
            assert item.velocity_fast >= item.velocity_moderate, item.skill_id


def test_served_bound_matches_the_pipeline_clamp() -> None:
    """The API keeps its own copy (no `pipelines` import at runtime); it must not drift."""
    from app.features.trends import velocity
    from pipelines.trends import score

    assert (velocity.V_CLAMP_MIN, velocity.V_CLAMP_MAX) == (score.V_CLAMP_MIN, score.V_CLAMP_MAX)
    for value in (-5.0, -2.0, -0.3, 0.0, 1.7, 2.0, 9.0):
        expected = score.clamp(value, score.V_CLAMP_MIN, score.V_CLAMP_MAX)
        assert velocity.served_velocity(value) == expected
