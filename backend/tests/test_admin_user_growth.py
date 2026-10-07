from datetime import date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.application.admin_user_growth import (
    _cohort_query,
    _login_activity_query,
    get_admin_user_growth_summary,
)


class StubResult:
    def __init__(self, row):
        self.row = row

    def one(self):
        return self.row


class StubSession:
    def __init__(self, rows):
        self.rows = list(rows)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return StubResult(self.rows.pop(0))


def test_growth_queries_use_user_counts_without_selecting_personal_details():
    start_at = datetime(2026, 9, 1)
    end_at = datetime(2026, 10, 1)
    cohort_sql = str(
        _cohort_query(start_at, end_at).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    activity_sql = str(
        _login_activity_query(start_at, end_at).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "users.phone" not in cohort_sql
    assert "users.name" not in cohort_sql
    assert "users.password_hash" not in cohort_sql
    assert "service_requests.service_type = 'report'" in cohort_sql
    assert "calendar_requests.status IN ('fulfilled', 'delivered')" in cohort_sql
    assert "users.last_login_at >= '2026-09-01 00:00:00'" in activity_sql
    assert "users.last_login_at < '2026-10-01 00:00:00'" in activity_sql


@pytest.mark.asyncio
async def test_growth_summary_reports_deduplicated_conversion_and_return_rates():
    db = StubSession(
        [
            SimpleNamespace(
                registered_users=10,
                profile_completed_users=8,
                applicant_users=6,
                delivered_users=4,
                report_applicant_users=5,
                report_delivered_users=3,
                calendar_applicant_users=3,
                calendar_delivered_users=2,
            ),
            SimpleNamespace(
                active_login_users=7,
                existing_user_base=4,
                returning_users=2,
            ),
        ]
    )

    summary = await get_admin_user_growth_summary(
        db,
        start_at=datetime(2026, 9, 1),
        end_at=datetime(2026, 10, 1),
        range_start=date(2026, 9, 1),
        range_end=date(2026, 9, 30),
    )

    assert summary.registered_users == 10
    assert summary.profile_completion_rate_percent == 80
    assert summary.applicant_users == 6
    assert summary.applicant_rate_percent == 60
    assert summary.delivered_users == 4
    assert summary.delivery_rate_percent == 66.7
    assert summary.active_login_users == 7
    assert summary.returning_users == 2
    assert summary.existing_user_login_rate_percent == 50
    assert [item.applicant_users for item in summary.by_service] == [5, 3]
    assert [item.delivery_rate_percent for item in summary.by_service] == [60, 66.7]
    assert len(db.statements) == 2


@pytest.mark.asyncio
async def test_growth_summary_uses_null_rates_when_denominators_are_empty():
    db = StubSession(
        [
            SimpleNamespace(
                registered_users=0,
                profile_completed_users=0,
                applicant_users=0,
                delivered_users=0,
                report_applicant_users=0,
                report_delivered_users=0,
                calendar_applicant_users=0,
                calendar_delivered_users=0,
            ),
            SimpleNamespace(active_login_users=0, existing_user_base=0, returning_users=0),
        ]
    )

    summary = await get_admin_user_growth_summary(
        db,
        start_at=datetime(2026, 9, 1),
        end_at=datetime(2026, 10, 1),
        range_start=date(2026, 9, 1),
        range_end=date(2026, 9, 30),
    )

    assert summary.profile_completion_rate_percent is None
    assert summary.applicant_rate_percent is None
    assert summary.delivery_rate_percent is None
    assert summary.existing_user_login_rate_percent is None
    assert all(channel.delivery_rate_percent is None for channel in summary.by_service)
