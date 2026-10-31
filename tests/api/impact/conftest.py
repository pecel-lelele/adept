from collections.abc import Iterator

import pytest

from app.features.impact import service


@pytest.fixture(autouse=True)
def _fresh_impact_summary() -> Iterator[None]:
    """Each test sees a summary computed from its own catalogue and snapshot."""
    service.clear_summary_cache()
    yield
    service.clear_summary_cache()
