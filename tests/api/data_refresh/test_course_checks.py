"""A responding URL does not re-date manual course facts or silently accept a dead page."""

import time
from dataclasses import replace
from datetime import date

import httpx

from app.features.data_refresh.course_checks import checked_rows, price_present
from app.features.pathway.catalogue_sources import MANUAL


def test_manual_fee_date_survives_even_a_successful_link_and_price_check() -> None:
    row = replace(MANUAL[0], verified_at=date(2026, 1, 2), cost_myr=149.0)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                text="<html><title>Public course</title>RM 149.00</html>",
                headers={"content-type": "text/html"},
            )
        )
    ) as client:
        accepted = checked_rows([row], client, time.monotonic() + 5)
    assert accepted[0].verified_at == date(2026, 1, 2)
    assert "matches the stored fee" in accepted[0].price_note


def test_dead_or_soft_404_page_cannot_be_verified() -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200,
                text="<title>404 Page not found</title>",
                headers={"content-type": "text/html"},
            )
        )
    ) as client:
        assert checked_rows([MANUAL[0]], client, time.monotonic() + 5) == []


def test_fee_check_rejects_an_unrelated_number() -> None:
    assert price_present("Harga: MYR 1,500.00", 1500)
    assert price_present("Kursus percuma", 0)
    assert not price_present("149 learners · RM 1490.00", 149)
