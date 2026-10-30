"""A posting's primary location cannot be overridden by employer offices."""

from typing import Any

import pytest

from pipelines.jobs import sources
from pipelines.jobs.boards import Board


class FakeFetcher(sources.Fetcher):
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def get_json(self, url: str, **kwargs: Any) -> Any:
        return self.payload


@pytest.mark.parametrize("place", ["Dubai, UAE", "Singapore", "Hong Kong", "New York, US"])
@pytest.mark.parametrize("connector", ["greenhouse", "lever", "ashby"])
def test_foreign_primary_location_overrides_other_offices(place: str, connector: str) -> None:
    job = {
        "id": "synthetic-job",
        "title": "Synthetic analyst",
        "location": {"name": place} if connector == "greenhouse" else place,
        "offices": [{"location": "Kuala Lumpur, Malaysia"}],
        "categories": {"location": place, "allLocations": ["Kuala Lumpur, Malaysia"]},
        "secondaryLocations": [{"location": "Kuala Lumpur, Malaysia"}],
        "address": {"postalAddress": {"addressCountry": "Malaysia"}},
    }
    payload = [job] if connector == "lever" else {"jobs": [job]}
    fetch = getattr(sources, connector)
    assert list(fetch(FakeFetcher(payload), Board(connector, "synthetic", "Synthetic"))) == []


@pytest.mark.parametrize("place", ["Kuala Lumpur, Malaysia", "Remote - Malaysia"])
def test_keeps_malaysian_and_remote_malaysian_postings(place: str) -> None:
    job = {
        "id": "synthetic-job",
        "title": "Synthetic analyst",
        "location": {"name": place},
        "offices": [{"location": "Singapore"}],
    }
    postings = list(sources.greenhouse(FakeFetcher({"jobs": [job]}), Board("greenhouse", "s", "S")))
    assert len(postings) == 1
    assert postings[0].location == place
    if place.startswith("Remote"):
        assert postings[0].remote_scope == "Malaysia"


def test_country_codes_and_place_boundaries() -> None:
    assert sources.in_malaysia("MY")
    assert not sources.in_malaysia("Singapore", "Malaysia")
    assert not sources.in_malaysia("Somewhere near Ipohville")
