"""Opt-in real pool regression; creates and drops its own synthetic database only.

Run with ADEPT_TEST_PG_ADMIN_URL pointing to a local PostgreSQL admin database.
"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.contracts.funding import FundingDecision, FundingRequest, FundingSubmission, MemberBudgetIn
from app.contracts.pathway import CompletionEvidence
from app.core import accounts, db, refdata
from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.features.org import funding
from app.features.pathway import repository

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not os.environ.get("ADEPT_TEST_PG_ADMIN_URL"), reason="local PostgreSQL opt-in")
def test_ten_concurrent_approvals_and_claim_payment_with_one_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = os.environ["ADEPT_TEST_PG_ADMIN_URL"]
    name = "adept_funding_test_" + uuid4().hex[:12]
    params = conninfo_to_dict(admin)
    params["dbname"] = name
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        with monkeypatch.context() as scoped:
            scoped.setenv("DATABASE_URL", make_conninfo(**params))
            scoped.setenv("M3_BACKEND", "postgres")
            scoped.setenv("DB_POOL_MAX", "1")
            db.close_pools()
            refdata.invalidate()
            get_settings.cache_clear()
            for script in ("src/db/migrate.py", "src/db/seed.py"):
                subprocess.run(
                    [sys.executable, str(ROOT / script)],
                    cwd=ROOT,
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
            with psycopg.connect(**params) as conn:
                conn.execute(
                    "INSERT INTO users(id,display_name,kind,is_synthetic) "
                    "VALUES ('synthetic-hr','Synthetic HR','org_admin',true)"
                )
                conn.execute(
                    "INSERT INTO organizations(id,type,name,industry,size,join_code) "
                    "VALUES ('synthetic-org','company','Synthetic org','Test',10,'SYNTEST1')"
                )
                conn.execute(
                    "INSERT INTO memberships(user_id,org_id,role,intake_status) "
                    "VALUES ('synthetic-hr','synthetic-org','manager','complete')"
                )
                for i in range(10):
                    uid = f"synthetic-member-{i}"
                    conn.execute(
                        "INSERT INTO users(id,display_name,kind,is_synthetic) "
                        "VALUES (%s,'Synthetic member','learner',true)",
                        (uid,),
                    )
                    conn.execute(
                        "INSERT INTO memberships(user_id,org_id,role,intake_status) "
                        "VALUES (%s,'synthetic-org','member','complete')",
                        (uid,),
                    )
            hr = CurrentUser("synthetic-hr", "Synthetic HR", "org_admin", "synthetic-org")
            members = [
                CurrentUser(f"synthetic-member-{i}", "Synthetic member", "learner", "synthetic-org")
                for i in range(10)
            ]
            year = funding.current_year()
            claims = []
            for member in members:
                funding.budget(hr, year, MemberBudgetIn(user_id=member.id, amount_myr=Decimal(600)))
                claims.append(
                    funding.request(
                        member,
                        year,
                        FundingRequest(
                            course_id="aitraining2u-ai-data-analytics",
                            role_id="data-analyst",
                            amount_myr=Decimal(500),
                            quote_url="https://example.com/synthetic-quote",
                        ),
                    ).claims[0]
                )

            def approve(claim):
                return funding.decide(
                    hr, year, claim.id, FundingDecision(revision=1, action="approve")
                )

            with ThreadPoolExecutor(max_workers=10) as pool:
                assert len(list(pool.map(approve, claims))) == 10
                reads = list(pool.map(lambda _: funding.ledger(hr, year), range(10)))
            assert all(len(result.claims) == 10 for result in reads)
            assert all(c.status == "approved" for c in reads[-1].claims)
            assert all(b.reserved_myr == 500 for b in reads[-1].budgets)
            assert db._pool(get_settings().database_url).max_size == 1

            member = members[0]
            claim = funding.ledger(member, year).claims[0]
            repository.set_course_status(
                member.id,
                claim.role_id,
                claim.course.id,
                "completed",
                claim.course,
                scope=repository.org_scope("synthetic-org"),
            )
            repository.save_evidence(
                member.id,
                CompletionEvidence(
                    role_id=claim.role_id,
                    course_id=claim.course.id,
                    kind="org_confirmed",
                    url="https://example.com/synthetic-certificate",
                    submitted_at=datetime.now(UTC),
                    reviewed_by=hr.id,
                    reviewed_at=datetime.now(UTC),
                    scope=repository.org_scope("synthetic-org"),
                ),
            )
            submitted = funding.submit(
                member,
                year,
                claim.id,
                FundingSubmission(
                    revision=claim.revision,
                    amount_myr=Decimal(450),
                    receipt_url="https://example.com/synthetic-receipt",
                    receipt_reference="SYN-001",
                    purchased_at=datetime.now(UTC),
                ),
            ).claims[0]
            accepted = funding.decide(
                hr,
                year,
                claim.id,
                FundingDecision(
                    revision=submitted.revision,
                    action="accept_claim",
                ),
            )
            payable = next(c for c in accepted.claims if c.id == claim.id)
            paid = funding.decide(
                hr,
                year,
                claim.id,
                FundingDecision(
                    revision=payable.revision,
                    action="mark_paid",
                    payment_reference="SYN-PAY-001",
                ),
            )
            assert next(c for c in paid.claims if c.id == claim.id).status == "paid"
    finally:
        db.close_pools()
        refdata.invalidate()
        get_settings.cache_clear()
        for uid in ["synthetic-hr", *(f"synthetic-member-{i}" for i in range(10))]:
            accounts.forget(uid)
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
