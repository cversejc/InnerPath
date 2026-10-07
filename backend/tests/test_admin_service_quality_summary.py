from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.application.admin_service_quality import _summary_query, get_admin_service_quality_summary


class StubRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class StubSession:
    def __init__(self, results):
        self.results = list(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return StubRows(self.results.pop(0))


def test_quality_summary_query_reads_aggregate_fields_without_feedback_text():
    sql = str(
        _summary_query(datetime(2026, 9, 1), datetime(2026, 10, 1)).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "service_feedback.comment" not in sql
    assert "service_feedback.resolution" not in sql
    assert "service_requests.consultation_type" in sql
    assert "service_requests.assigned_psychology_consultant_id" in sql
    assert "service_feedback.created_at >= '2026-09-01 00:00:00'" in sql
    assert "service_feedback.created_at < '2026-10-01 00:00:00'" in sql


@pytest.mark.asyncio
async def test_quality_summary_groups_service_specialty_consultant_and_resolution_metrics():
    now = datetime(2026, 10, 6, 8)
    report_complaint = SimpleNamespace(
        id=1,
        service_request_id=11,
        calendar_request_id=None,
        feedback_type="COMPLAINT",
        rating=2,
        status="RESOLVED",
        created_at=now - timedelta(days=8),
        resolved_at=now - timedelta(days=6),
        consultation_type="psychology",
        assigned_consultant_id=None,
        assigned_mingli_consultant_id=3,
        assigned_psychology_consultant_id=4,
    )
    calendar_suggestion = SimpleNamespace(
        id=2,
        service_request_id=None,
        calendar_request_id=21,
        feedback_type="SUGGESTION",
        rating=None,
        status="IN_PROGRESS",
        created_at=now - timedelta(days=2),
        resolved_at=None,
        consultation_type=None,
        assigned_consultant_id=None,
        assigned_mingli_consultant_id=None,
        assigned_psychology_consultant_id=None,
    )
    report_praise = SimpleNamespace(
        id=3,
        service_request_id=12,
        calendar_request_id=None,
        feedback_type="PRAISE",
        rating=4,
        status="NEW",
        created_at=now - timedelta(days=1),
        resolved_at=None,
        consultation_type="metaphysics",
        assigned_consultant_id=5,
        assigned_mingli_consultant_id=None,
        assigned_psychology_consultant_id=None,
    )
    db = StubSession([
        [report_complaint, calendar_suggestion, report_praise],
        [SimpleNamespace(id=3, name="咨询师甲"), SimpleNamespace(id=4, name="咨询师乙"), SimpleNamespace(id=5, name="咨询师丙")],
    ])

    result = await get_admin_service_quality_summary(db, period_days=30, now=now)
    summary = result

    assert summary.totals.feedback_count == 3
    assert summary.totals.rated_count == 2
    assert summary.totals.average_rating == 3
    assert summary.totals.complaint_count == 1
    assert summary.totals.resolution_rate_percent == 33.3
    assert summary.totals.resolution_p50_hours == 48
    assert summary.totals.resolution_p90_hours == 48
    assert {item.key: item.feedback_count for item in summary.by_service} == {
        "report": 2,
        "calendar": 1,
    }
    assert {item.key: item.feedback_count for item in summary.by_specialty}["psychology"] == 1
    assert {item.consultant_id: item.feedback_count for item in summary.by_consultant} == {
        3: 1,
        4: 1,
        5: 1,
    }
    assert len(summary.weekly_trend) == 6
    assert len(db.statements) == 2
    assert not db.results


@pytest.mark.asyncio
async def test_quality_summary_empty_range_returns_zero_metrics_without_consultant_query():
    now = datetime(2026, 10, 6, 8)
    db = StubSession([[]])

    summary = await get_admin_service_quality_summary(db, period_days=7, now=now)

    assert summary.totals.feedback_count == 0
    assert summary.totals.average_rating is None
    assert summary.totals.resolution_rate_percent is None
    assert all(group.feedback_count == 0 for group in summary.by_service)
    assert len(db.statements) == 1
