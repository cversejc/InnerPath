from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.application.admin_consultant_workload import (
    consultant_active_request_preview,
    consultant_request_assignments,
    consultant_work_events,
)
from app.schemas.admin import AdminConsultantWorkloadItem


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


def test_consultant_workload_schema_includes_stalled_work_preview():
    item = AdminConsultantWorkloadItem.model_validate(
        {
            "consultant_id": 9,
            "stale_active_requests": 1,
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
