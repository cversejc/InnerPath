from datetime import date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.application import admin_generation_observability
from app.application.admin_generation_observability import (
    _calendar_request_query,
    _outbox_query,
    _report_case_query,
    _skill_run_query,
    get_admin_generation_summary,
)


class StubRows:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def one(self):
        return self.rows[0]


class StubSession:
    def __init__(self, results):
        self.results = list(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return StubRows(self.results.pop(0))


class StubSavepointSession:
    def __init__(self):
        self.rolled_back = False

    def begin_nested(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, error_type, _error, _traceback):
        self.rolled_back = error_type is not None
        return False


def test_generation_queries_exclude_prompts_outputs_and_raw_errors():
    now = datetime(2026, 10, 6, 8)
    skill_sql = str(
        _skill_run_query(datetime(2026, 9, 1), datetime(2026, 10, 1)).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    calendar_sql = str(
        _calendar_request_query(now).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    outbox_sql = str(
        _outbox_query(now).compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    case_sql = str(_report_case_query().compile(dialect=postgresql.dialect()))

    for sensitive_column in (
        "skill_runs.input_snapshot",
        "skill_runs.output_raw",
        "skill_runs.output_parsed",
        "skill_runs.error",
        "calendar_requests.input_snapshot",
        "calendar_requests.generation_error",
        "workflow_outbox.payload_json",
    ):
        assert sensitive_column not in skill_sql + calendar_sql + outbox_sql + case_sql
    assert "skill_runs.completed_at >= '2026-09-01 00:00:00'" in skill_sql
    assert "skill_runs.report_case_id IS NOT NULL" in skill_sql
    assert "calendar_requests.updated_at < '2026-10-06 07:15:00'" in calendar_sql
    assert "workflow_outbox.created_at < '2026-10-06 07:55:00'" in outbox_sql


@pytest.mark.asyncio
async def test_generation_summary_aggregates_stage_health_and_current_queues():
    db = StubSession(
        [
            [
                SimpleNamespace(
                    stage_key="REPORT_FRAGMENT",
                    active_runs=2,
                    completed_runs=8,
                    failed_runs=2,
                    retry_attempts=3,
                    p50_duration_hours=0.25,
                    p90_duration_hours=1.5,
                ),
                SimpleNamespace(
                    stage_key="CALENDAR_PRODUCTION",
                    active_runs=1,
                    completed_runs=4,
                    failed_runs=0,
                    retry_attempts=1,
                    p50_duration_hours=0.5,
                    p90_duration_hours=0.8,
                ),
            ],
            [
                SimpleNamespace(
                    created=1,
                    active=7,
                    blocked=2,
                    ready_to_deliver=3,
                    delivered=21,
                    cancelled=4,
                )
            ],
            [
                SimpleNamespace(
                    queued=2,
                    generating=1,
                    failed=3,
                    delivered=9,
                    stalled=1,
                )
            ],
            [
                SimpleNamespace(
                    pending=5,
                    pending_over_5m=2,
                    failed=1,
                    published=17,
                    retry_attempts=4,
                )
            ],
        ]
    )

    summary = await get_admin_generation_summary(
        db,
        start_at=datetime(2026, 9, 1),
        end_at=datetime(2026, 10, 1),
        range_start=date(2026, 9, 1),
        range_end=date(2026, 9, 30),
        now=datetime(2026, 10, 6, 8),
    )

    assert summary.active_runs == 3
    assert summary.completed_runs == 12
    assert summary.failed_runs == 2
    assert summary.success_rate_percent == 85.7
    assert summary.retry_attempts == 4
    assert {stage.stage_key: stage.label for stage in summary.stages} == {
        "REPORT_FRAGMENT": "报告正文生成",
        "CALENDAR_PRODUCTION": "日历生成",
    }
    assert summary.report_cases_created == 1
    assert summary.report_cases_cancelled == 4
    assert summary.report_cases_blocked == 2
    assert summary.calendar_queued == 2
    assert summary.calendar_stalled == 1
    assert summary.outbox_pending_over_5m == 2
    assert summary.outbox_published == 17
    assert summary.outbox_retry_attempts == 4
    assert len(db.statements) == 4


@pytest.mark.asyncio
async def test_generation_summary_preserves_null_success_rate_without_terminal_runs():
    db = StubSession(
        [
            [
                SimpleNamespace(
                    stage_key="REPORT_FRAGMENT",
                    active_runs=1,
                    completed_runs=0,
                    failed_runs=0,
                    retry_attempts=0,
                    p50_duration_hours=None,
                    p90_duration_hours=None,
                )
            ],
            [SimpleNamespace(created=0, active=0, blocked=0, ready_to_deliver=0, delivered=0, cancelled=0)],
            [SimpleNamespace(queued=0, generating=0, failed=0, delivered=0, stalled=0)],
            [SimpleNamespace(pending=0, pending_over_5m=0, failed=0, published=0, retry_attempts=0)],
        ]
    )

    summary = await get_admin_generation_summary(
        db,
        start_at=datetime(2026, 9, 1),
        end_at=datetime(2026, 10, 1),
        range_start=date(2026, 9, 1),
        range_end=date(2026, 9, 30),
        now=datetime(2026, 10, 6, 8),
    )

    assert summary.active_runs == 1
    assert summary.success_rate_percent is None
    assert summary.stages[0].p50_duration_hours is None


@pytest.mark.asyncio
async def test_generation_summary_failure_is_contained_by_savepoint(monkeypatch, caplog):
    db = StubSavepointSession()

    async def fail_summary(*_args, **_kwargs):
        raise RuntimeError("private query detail")

    monkeypatch.setattr(
        admin_generation_observability, "get_admin_generation_summary", fail_summary
    )

    summary = await admin_generation_observability.load_admin_generation_summary(
        db,
        start_at=datetime(2026, 9, 1),
        end_at=datetime(2026, 10, 1),
        range_start=date(2026, 9, 1),
        range_end=date(2026, 9, 30),
    )

    assert summary is None
    assert db.rolled_back is True
    assert "RuntimeError" in caplog.text
    assert "private query detail" not in caplog.text
