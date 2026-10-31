"""DOSM public CSV -> latest complete month -> validated rates -> saved national context.

Evaluation validates dates/rates and source metadata; serving reads PostgreSQL or its dated
seed export. National survey rates are not mapped to occupations or blended into role scores.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import io
import os
from contextlib import nullcontext
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import psycopg
from psycopg.types.json import Jsonb

from app.contracts.common import RecommendationMeta, Source
from app.contracts.labour import MalaysiaLabourContext

SOURCE_URL = "https://open.dosm.gov.my/data-catalogue/lfs_month"
CSV_URL = "https://storage.dosm.gov.my/labour/lfs_month.csv"
SEED = Path(__file__).resolve().parents[2] / "data/seed/trends/malaysia_labour.json"
MAX_BYTES = 1_000_000


def parse_latest(text: str, retrieved: date) -> MalaysiaLabourContext:
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("DOSM returned no monthly observations")
    row = max(rows, key=lambda value: date.fromisoformat(value["date"]))
    month = date.fromisoformat(row["date"])
    end = month.replace(day=calendar.monthrange(month.year, month.month)[1])
    if month.day != 1 or end > retrieved:
        raise ValueError("DOSM observation month is incomplete or invalid")
    return MalaysiaLabourContext(
        observed_month=month,
        unemployment_rate=float(row["u_rate"]),
        participation_rate=float(row["p_rate"]),
        employment_population_ratio=float(row["ep_ratio"]),
        meta=RecommendationMeta(
            sources=[
                Source(
                    name="Department of Statistics Malaysia: monthly Labour Force Survey",
                    url=SOURCE_URL,
                    retrieved_at=retrieved,
                )
            ],
            snapshot_date=month,
            scenario="moderate",
            is_estimate=False,
            observed_from=month,
            observed_to=end,
        ),
    )


def fetch() -> MalaysiaLabourContext:
    # Fixed public host, no credentials, no redirects, bounded time and decoded response size.
    with httpx.Client(timeout=20, follow_redirects=False) as client:
        with client.stream("GET", CSV_URL) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise ValueError("DOSM CSV exceeds the response size limit")
    return parse_latest(data.decode("utf-8-sig"), datetime.now(UTC).date())


def publish(
    value: MalaysiaLabourContext, url: str, *, conn: psycopg.Connection | None = None
) -> None:
    connection = (
        nullcontext(conn)
        if conn is not None
        else psycopg.connect(url, connect_timeout=5, options="-c statement_timeout=10000")
    )
    with connection as conn:
        conn.execute(
            "INSERT INTO malaysia_labour_context(observed_month,payload) VALUES (%s,%s) "
            "ON CONFLICT(observed_month) DO UPDATE SET payload=EXCLUDED.payload",
            (value.observed_month, Jsonb(value.model_dump(mode="json"))),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db", action="store_true", help="publish to explicitly configured DATABASE_URL"
    )
    parser.add_argument("--output", type=Path, default=SEED)
    args = parser.parse_args()
    if args.db and not os.environ.get("DATABASE_URL"):
        raise ValueError("DATABASE_URL must be explicitly set")
    value = fetch()
    if args.db:
        publish(value, os.environ["DATABASE_URL"])
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(value.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(
        f"DOSM observed month {value.observed_month}; "
        f"retrieved {value.meta.sources[0].retrieved_at}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
