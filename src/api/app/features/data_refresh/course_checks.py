"""Bounded course-link/price checks; manual facts keep their original verification dates."""

from __future__ import annotations

import html
import re
import time
from dataclasses import replace

import httpx

from app.features.pathway.catalogue_sources import CourseRow

MAX_PAGE_BYTES = 2_000_000


def price_present(text: str, amount: float) -> bool:
    plain = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).lower().split())
    if amount == 0:
        return bool(re.search(r"\b(free|percuma)\b", plain))
    price = f"{amount:,.2f}"
    return bool(re.search(r"(?:rm|myr)\s*" + re.escape(price) + r"(?!\d)", plain))


def checked_rows(rows: list[CourseRow], client: httpx.Client, deadline: float) -> list[CourseRow]:
    accepted = []
    for row in rows:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("Course verification incomplete; previous catalogue retained")
        try:
            with client.stream("GET", row.url, timeout=min(5, left)) as response:
                response.raise_for_status()
                if not any(
                    kind in response.headers.get("content-type", "")
                    for kind in ("text/html", "application/pdf")
                ):
                    continue
                body = bytearray()
                for chunk in response.iter_bytes():
                    if time.monotonic() >= deadline:
                        raise TimeoutError("course checks reached their deadline")
                    body.extend(chunk)
                    if len(body) > MAX_PAGE_BYTES:
                        raise ValueError("course page exceeds its size limit")
            if not body:
                continue
            text = body.decode("utf-8", errors="replace")
            if re.search(r"<title[^>]*>\s*(?:404|page not found)", text, re.I):
                continue
            if (
                row.provider != "Microsoft Learn"
                or row.source_name != "Microsoft Learn Catalog API"
            ):
                status = (
                    "matches the stored fee"
                    if price_present(text, row.cost_myr)
                    else "did not reconfirm the stored fee"
                )
                row = replace(
                    row,
                    price_note=(
                        row.price_note + f" Automatic URL check succeeded and {status}; "
                        "existing fact-verification date retained. "
                        "Confirm current price and eligibility with the provider."
                    ).strip(),
                )
            accepted.append(row)
        except (httpx.HTTPError, TimeoutError, ValueError):
            continue  # unavailable source: preserve its existing record and verification date
    return accepted
