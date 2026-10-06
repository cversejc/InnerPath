"""Read-only generation and workflow queue health for the admin overview."""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.calendar.models import CalendarRequest
from app.domains.skills.models import SkillRun
from app.domains.workflow.models import ReportCase, WorkflowOutbox
from app.schemas.admin import AdminGenerationStage, AdminGenerationSummary


STAGE_LABELS = {
    "CALENDAR_PRODUCTION": "日历生成",
    "REPORT_FRAGMENT": "报告正文生成",
    "REPORT_CHAPTER_COHERENCE": "章节一致性检查",
    "REPORT_COHERENCE": "报告一致性检查",
    "REPORT_QA": "报告质量检查",
}
logger = logging.getLogger(__name__)


def _skill_run_query(start_at: datetime, end_at: datetime):
    active = SkillRun.status.in_(("PENDING", "RUNNING"))
    completed_in_range = and_(
        SkillRun.status == "COMPLETED",
        SkillRun.completed_at >= start_at,
        SkillRun.completed_at < end_at,
    )
    failed_in_range = and_(
        SkillRun.status == "FAILED",
        SkillRun.completed_at >= start_at,
        SkillRun.completed_at < end_at,
    )
    terminal_in_range = or_(completed_in_range, failed_in_range)
    duration_in_range = and_(
        terminal_in_range,
        SkillRun.started_at.is_not(None),
        SkillRun.completed_at >= SkillRun.started_at,
    )
    duration_hours = func.extract(
        "epoch", SkillRun.completed_at - SkillRun.started_at
    ) / 3600.0
    valid_duration_hours = case((duration_in_range, duration_hours))
    relevant_run = or_(
        SkillRun.report_case_id.is_not(None),
        SkillRun.target_type == "CALENDAR_PRODUCTION",
    )
    return (
        select(
            SkillRun.target_type.label("stage_key"),
            func.count(case((active, SkillRun.id))).label("active_runs"),
            func.count(case((completed_in_range, SkillRun.id))).label("completed_runs"),
            func.count(case((failed_in_range, SkillRun.id))).label("failed_runs"),
            func.coalesce(
                func.sum(
                    case((terminal_in_range, SkillRun.retry_count), else_=0)
                ),
                0,
            ).label("retry_attempts"),
            func.percentile_cont(0.5)
            .within_group(valid_duration_hours)
            .label("p50_duration_hours"),
            func.percentile_cont(0.9)
            .within_group(valid_duration_hours)
            .label("p90_duration_hours"),
        )
        .where(
            relevant_run,
            or_(active, terminal_in_range),
        )
        .group_by(SkillRun.target_type)
        .order_by(SkillRun.target_type)
    )


def _report_case_query():
    return select(
        func.count(case((ReportCase.status == "CREATED", ReportCase.id))).label(
            "created"
        ),
        func.count(case((ReportCase.status == "ACTIVE", ReportCase.id))).label(
            "active"
        ),
        func.count(case((ReportCase.status == "BLOCKED", ReportCase.id))).label(
            "blocked"
        ),
        func.count(
            case((ReportCase.status == "READY_TO_DELIVER", ReportCase.id))
        ).label("ready_to_deliver"),
        func.count(case((ReportCase.status == "DELIVERED", ReportCase.id))).label(
            "delivered"
        ),
        func.count(case((ReportCase.status == "CANCELLED", ReportCase.id))).label(
            "cancelled"
        ),
    ).select_from(ReportCase)


def _calendar_request_query(now: datetime):
    stalled_cutoff = now - timedelta(minutes=45)
    active_status = CalendarRequest.status.in_(
        ("queued", "pending", "generating", "processing")
    )
    return select(
        func.count(
            case((CalendarRequest.status.in_(("queued", "pending")), CalendarRequest.id))
        ).label("queued"),
        func.count(
            case(
                (CalendarRequest.status.in_(("generating", "processing")), CalendarRequest.id)
            )
        ).label("generating"),
        func.count(case((CalendarRequest.status == "failed", CalendarRequest.id))).label(
            "failed"
        ),
        func.count(
            case(
                (CalendarRequest.status.in_(("fulfilled", "delivered")), CalendarRequest.id)
            )
        ).label("delivered"),
        func.count(
            case(
                (
                    and_(
                        CalendarRequest.status == "generating",
                        CalendarRequest.updated_at < stalled_cutoff,
                    ),
                    CalendarRequest.id,
                )
            )
        ).label("stalled"),
    ).select_from(CalendarRequest).where(
        or_(active_status, CalendarRequest.status.in_(("failed", "fulfilled", "delivered")))
    )


def _outbox_query(now: datetime):
    overdue_cutoff = now - timedelta(minutes=5)
    return select(
        func.count(case((WorkflowOutbox.status == "PENDING", WorkflowOutbox.id))).label(
            "pending"
        ),
        func.count(
            case(
                (
                    and_(
                        WorkflowOutbox.status == "PENDING",
                        WorkflowOutbox.created_at < overdue_cutoff,
                    ),
                    WorkflowOutbox.id,
                )
            )
        ).label("pending_over_5m"),
        func.count(case((WorkflowOutbox.status == "FAILED", WorkflowOutbox.id))).label(
            "failed"
        ),
        func.count(
            case((WorkflowOutbox.status == "PUBLISHED", WorkflowOutbox.id))
        ).label("published"),
        func.coalesce(
            func.sum(
                case(
                    (WorkflowOutbox.status == "PENDING", WorkflowOutbox.retry_count),
                    else_=0,
                )
            ),
            0,
        ).label("retry_attempts"),
    ).select_from(WorkflowOutbox)


def _rounded(value) -> float | None:
    return round(float(value), 1) if value is not None else None


async def get_admin_generation_summary(
    db: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
    range_start: date,
    range_end: date,
    now: datetime | None = None,
) -> AdminGenerationSummary:
    current_time = now or datetime.utcnow()
    stage_rows = (await db.execute(_skill_run_query(start_at, end_at))).all()
    case_summary = (
        await db.execute(_report_case_query())
    ).one()
    calendar_summary = (
        await db.execute(_calendar_request_query(current_time))
    ).one()
    outbox_summary = (await db.execute(_outbox_query(current_time))).one()

    stages = [
        AdminGenerationStage(
            stage_key=row.stage_key,
            label=STAGE_LABELS.get(row.stage_key, "其他报告处理"),
            active_runs=int(row.active_runs or 0),
            completed_runs=int(row.completed_runs or 0),
            failed_runs=int(row.failed_runs or 0),
            retry_attempts=int(row.retry_attempts or 0),
            p50_duration_hours=_rounded(row.p50_duration_hours),
            p90_duration_hours=_rounded(row.p90_duration_hours),
        )
        for row in stage_rows
    ]
    completed_runs = sum(stage.completed_runs for stage in stages)
    failed_runs = sum(stage.failed_runs for stage in stages)
    terminal_runs = completed_runs + failed_runs

    return AdminGenerationSummary(
        range_start=range_start,
        range_end=range_end,
        active_runs=sum(stage.active_runs for stage in stages),
        completed_runs=completed_runs,
        failed_runs=failed_runs,
        success_rate_percent=(
            round(completed_runs * 100 / terminal_runs, 1) if terminal_runs else None
        ),
        retry_attempts=sum(stage.retry_attempts for stage in stages),
        stages=stages,
        report_cases_created=int(case_summary.created or 0),
        report_cases_active=int(case_summary.active or 0),
        report_cases_blocked=int(case_summary.blocked or 0),
        report_cases_ready_to_deliver=int(case_summary.ready_to_deliver or 0),
        report_cases_delivered=int(case_summary.delivered or 0),
        report_cases_cancelled=int(case_summary.cancelled or 0),
        calendar_queued=int(calendar_summary.queued or 0),
        calendar_generating=int(calendar_summary.generating or 0),
        calendar_failed=int(calendar_summary.failed or 0),
        calendar_delivered=int(calendar_summary.delivered or 0),
        calendar_stalled=int(calendar_summary.stalled or 0),
        outbox_pending=int(outbox_summary.pending or 0),
        outbox_pending_over_5m=int(outbox_summary.pending_over_5m or 0),
        outbox_failed=int(outbox_summary.failed or 0),
        outbox_published=int(outbox_summary.published or 0),
        outbox_retry_attempts=int(outbox_summary.retry_attempts or 0),
    )


async def load_admin_generation_summary(
    db: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
    range_start: date,
    range_end: date,
    now: datetime | None = None,
) -> AdminGenerationSummary | None:
    """Keep optional observability queries from failing the full dashboard."""
    try:
        async with db.begin_nested():
            return await get_admin_generation_summary(
                db,
                start_at=start_at,
                end_at=end_at,
                range_start=range_start,
                range_end=range_end,
                now=now,
            )
    except Exception as error:
        logger.warning(
            "admin_generation_summary_unavailable error_type=%s",
            type(error).__name__,
        )
        return None
