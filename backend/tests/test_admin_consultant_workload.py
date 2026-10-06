from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.application.admin_consultant_workload import (
    consultant_request_assignments,
    consultant_work_events,
)


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
