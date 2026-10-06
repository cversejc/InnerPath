from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace

import pytest

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.application.admin_consultant_workload import (
    consultant_active_status_counts,
    consultant_active_request_preview,
    consultant_delivered_request_cycles,
    consultant_request_assignments,
    consultant_specialty_load_counts,
    consultant_work_events,
    get_admin_consultant_workload,
    summarize_delivery_cycles,
)
from app.schemas.admin import AdminConsultantWorkloadItem, AdminConsultantWorkloadResponse


def compile_sql(statement):
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_consultant_request_assignments_deduplicate_specialty_slots():
    statement = select(consultant_request_assignments())
    sql = compile_sql(statement)

    assert "SELECT DISTINCT" in sql
    assert "assigned_mingli_consultant_id" in sql
    assert "assigned_psychology_consultant_id" in sql
    assert sql.count("UNION ALL") == 2


def test_consultant_work_events_track_performed_actions_not_admin_assignment():
    statement = select(consultant_work_events())
    sql = compile_sql(statement)

    assert "service_request.accept" in sql
    assert "service_request.specialty.accept" in sql
    assert "service_request.deliver" in sql
    assert "report_case.deliver" in sql
    assert "service_request.assignment.update" not in sql
    assert sql.count("UNION ALL") == 2


def test_active_consultant_work_preview_only_returns_oldest_open_requests():
    statement = consultant_active_request_preview([4, 7], limit=5)
    sql = compile_sql(statement).lower()

    assert "row_number() over" in sql
    assert "partition by consultant_request_assignments.consultant_id" in sql
    assert "service_requests.updated_at asc" in sql
    assert "service_requests.status not in ('delivered', 'withdrawn', 'rejected')" in sql
    assert "request_rank <= 5" in sql
    assert "in (4, 7)" in sql


def test_consultant_stage_counts_only_include_open_work():
    sql = compile_sql(consultant_active_status_counts([4, 7])).lower()

    assert "group by consultant_request_assignments.consultant_id, service_requests.status" in sql
    assert "service_requests.status not in ('delivered', 'withdrawn', 'rejected')" in sql
    assert "in (4, 7)" in sql


def test_consultant_specialty_load_counts_cover_single_and_collaborative_assignments():
    sql = compile_sql(
        consultant_specialty_load_counts(
            [4, 7],
            stale_cutoff=datetime(2026, 10, 1),
        )
    ).lower()

    assert "assigned_consultant_id" in sql
    assert "assigned_mingli_consultant_id" in sql
    assert "assigned_psychology_consultant_id" in sql
    assert "consultation_type in ('metaphysics', 'integrated')" in sql
    assert "consultation_type in ('psychology', 'integrated')" in sql
    assert "select distinct" in sql
    assert "group by consultant_specialty_request_assignments.consultant_id, consultant_specialty_request_assignments.specialty" in sql
    assert "service_requests.updated_at < '2026-10-01 00:00:00'" in sql


def test_consultant_delivery_cycles_use_delivered_reports_in_selected_period():
    sql = compile_sql(
        consultant_delivered_request_cycles([4], cutoff=datetime(2026, 10, 1))
    ).lower()

    assert "service_requests.service_type = 'report'" in sql
    assert "service_requests.status = 'delivered'" in sql
    assert "service_requests.delivered_at >= '2026-10-01 00:00:00'" in sql
    assert "service_requests.created_at" in sql
    assert "select distinct" in sql


def test_delivery_cycle_summary_reports_median_p90_and_empty_samples():
    summary = summarize_delivery_cycles([10, 1, 4, 7, 9, 2, 8, 3, 6, 5])

    assert summary == {
        "delivered_cycle_samples": 10,
        "delivery_cycle_p50_hours": 5.5,
        "delivery_cycle_p90_hours": 9.1,
    }
    assert summarize_delivery_cycles([]) == {
        "delivered_cycle_samples": 0,
        "delivery_cycle_p50_hours": None,
        "delivery_cycle_p90_hours": None,
    }


def test_consultant_workload_schema_includes_stalled_work_preview():
    item = AdminConsultantWorkloadItem.model_validate(
        {
            "consultant_id": 9,
            "stale_active_requests": 1,
            "active_by_status": [{"status": "reviewing", "request_count": 1}],
            "delivered_cycle_samples": 3,
            "delivery_cycle_p50_hours": 30.5,
            "delivery_cycle_p90_hours": 48,
            "specialty_load": [
                {
                    "specialty": "psychology",
                    "active_requests": 2,
                    "stale_active_requests": 1,
                }
            ],
            "active_request_preview": [
                {
                    "request_id": 31,
                    "user_id": 12,
                    "user_name": "测试用户",
                    "current_status": "reviewing",
                    "created_at": "2026-10-01T08:00:00",
                    "updated_at": "2026-10-02T08:00:00",
                    "age_hours": 120,
                    "idle_hours": 96,
                    "is_stale": True,
                }
            ],
        }
    )

    assert item.stale_active_requests == 1
    assert item.active_request_preview[0].request_id == 31
    assert item.active_request_preview[0].is_stale is True
    assert item.active_by_status[0].status == "reviewing"
    assert item.delivered_cycle_samples == 3
    assert item.delivery_cycle_p90_hours == 48
    assert item.specialty_load[0].specialty == "psychology"
    assert item.specialty_load[0].active_requests == 2
    assert item.specialty_load[0].stale_active_requests == 1


class StubRows:
    def __init__(self, rows):
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)

    def all(self):
        return self.rows


class StubSession:
    def __init__(self, query_rows):
        self.query_rows = query_rows
        self.statements = []

    async def scalars(self, statement):
        self.statements.append(statement)
        return StubRows([SimpleNamespace(id=9)])

    async def execute(self, statement):
        self.statements.append(statement)
        return StubRows(self.query_rows.pop(0))


@pytest.mark.asyncio
async def test_consultant_workload_is_read_only_and_combines_stage_and_cycle_metrics():
    now = datetime.utcnow()
    session = StubSession([
        [SimpleNamespace(consultant_id=9, total_requests=4, active_requests=2, stale_active_requests=1)],
        [SimpleNamespace(consultant_id=9, specialty="psychology", active_requests=2, stale_active_requests=1)],
        [
            SimpleNamespace(consultant_id=9, status="reviewing", request_count=1),
            SimpleNamespace(consultant_id=9, status="accepted", request_count=1),
        ],
        [SimpleNamespace(
            consultant_id=9,
            request_id=31,
            user_id=12,
            user_name="测试用户",
            consultation_type="psychology",
            current_status="reviewing",
            created_at=now - timedelta(hours=30),
            updated_at=now - timedelta(hours=2),
        )],
        [SimpleNamespace(
            consultant_id=9,
            created_at=now - timedelta(hours=36),
            delivered_at=now - timedelta(hours=12),
        )],
        [SimpleNamespace(consultant_id=9, accepted_in_period=2, delivered_in_period=1)],
        [SimpleNamespace(
            consultant_id=9,
            request_id=31,
            event_id=91,
            event_type="accepted",
            event_at=now - timedelta(hours=10),
            user_id=12,
            user_name="测试用户",
            consultation_type="psychology",
            current_status="reviewing",
        )],
    ])

    result = await get_admin_consultant_workload(session, period_days=30)
    response = AdminConsultantWorkloadResponse.model_validate(result)

    assert response.items[0].active_requests == 2
    assert [item.status for item in response.items[0].active_by_status] == [
        "accepted",
        "reviewing",
    ]
    assert response.items[0].delivered_cycle_samples == 1
    assert response.items[0].delivery_cycle_p50_hours == 24
    assert response.items[0].delivery_cycle_p90_hours == 24
    assert [item.model_dump() for item in response.items[0].specialty_load] == [
        {"specialty": "mingli", "active_requests": 0, "stale_active_requests": 0},
        {"specialty": "psychology", "active_requests": 2, "stale_active_requests": 1},
    ]
    assert len(session.statements) == 8
    assert not session.query_rows
