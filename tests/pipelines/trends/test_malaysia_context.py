from datetime import date

import pytest

from pipelines.trends.malaysia_context import parse_latest


def test_month_and_retrieval_are_distinct_and_latest_row_wins() -> None:
    csv = "date,u_rate,p_rate,ep_ratio\n2026-07-01,3.0,70.0,68.0\n2026-08-01,2.9,71.0,68.9\n"
    result = parse_latest(csv, date(2026, 10, 30))
    assert result.unemployment_rate == 2.9
    assert result.meta.snapshot_date == date(2026, 8, 1)
    assert result.meta.sources[0].retrieved_at == date(2026, 10, 30)
    assert result.meta.observed_to == date(2026, 8, 31)
    assert not result.meta.is_estimate


@pytest.mark.parametrize(
    "row", ["2026-10-01,3,70,68", "2026-08-01,nan,70,68", "2026-08-01,101,70,68"]
)
def test_invalid_or_incomplete_observations_are_not_published(row: str) -> None:
    with pytest.raises(ValueError):
        parse_latest("date,u_rate,p_rate,ep_ratio\n" + row, date(2026, 10, 15))
