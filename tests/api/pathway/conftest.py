from collections.abc import Iterator

import pytest

from app.features.pathway import repository


@pytest.fixture(autouse=True)
def _fresh_pathway_state() -> Iterator[None]:
    repository.reset()
    yield
    repository.reset()
