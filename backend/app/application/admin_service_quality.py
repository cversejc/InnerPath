"""Read-only service quality summaries for the admin feedback workspace."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import median, quantiles

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.feedback.models import ServiceFeedback
from app.domains.feedback.schemas import AdminServiceQualitySummary
from app.domains.service_requests.models import ServiceRequest
from app.models.user import User


SERVICE_LABELS = {"report": "报告", "calendar": "日历"}
SPECIALTY_LABELS = {
    "metaphysics": "命理",
    "psychology": "心理",
    "integrated": "综合",
    "unclassified": "未标注",
}


def _quality_metrics(rows) -> dict:
    rows = list(rows)
    ratings = [row.rating for row in rows if row.rating is not None]
    resolved = [row for row in rows if row.status == "RESOLVED"]
    resolution_hours = [
        (row.resolved_at - row.created_at).total_seconds() / 3600
        for row in resolved
        if row.resolved_at is not None
        and row.created_at is not None
        and row.resolved_at >= row.created_at
    ]
    resolution_hours.sort()
    p90 = (
        quantiles(resolution_hours, n=10, method="inclusive")[8]
        if len(resolution_hours) > 1
        else resolution_hours[0]
        if resolution_hours
        else None
    )
    return {
        "feedback_count": len(rows),
        "rated_count": len(ratings),
        "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "complaint_count": sum(row.feedback_type == "COMPLAINT" for row in rows),
        "resolved_count": len(resolved),
        "resolution_rate_percent": (
            round(len(resolved) * 100 / len(rows), 1) if rows else None
        ),
        "resolution_p50_hours": round(median(resolution_hours), 1)
        if resolution_hours
        else None,
        "resolution_p90_hours": round(p90, 1) if p90 is not None else None,
    }


def _consultant_rating_metrics(rows) -> dict:
    ratings = [row.rating for row in rows if row.rating is not None]
    return {
        "feedback_count": len(rows),
        "rated_count": len(ratings),
        "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "complaint_count": sum(row.feedback_type == "COMPLAINT" for row in rows),
    }


def _weekly_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _specialty_key(value: str | None) -> str:
    if value in {"metaphysics", "mingli"}:
        return "metaphysics"
    if value in {"psychology", "integrated"}:
        return value
    return "unclassified"


def _summary_query(cutoff: datetime, now: datetime):
    return (
        select(
            ServiceFeedback.id,
            ServiceFeedback.service_request_id,
            ServiceFeedback.calendar_request_id,
            ServiceFeedback.feedback_type,
            ServiceFeedback.rating,
            ServiceFeedback.status,
            ServiceFeedback.created_at,
            ServiceFeedback.resolved_at,
            ServiceRequest.consultation_type,
            ServiceRequest.assigned_consultant_id,
            ServiceRequest.assigned_mingli_consultant_id,
            ServiceRequest.assigned_psychology_consultant_id,
        )
        .outerjoin(
            ServiceRequest,
            ServiceRequest.id == ServiceFeedback.service_request_id,
        )
        .where(
            ServiceFeedback.created_at >= cutoff,
            ServiceFeedback.created_at < now,
        )
        .order_by(ServiceFeedback.created_at, ServiceFeedback.id)
    )


async def get_admin_service_quality_summary(
    db: AsyncSession,
    *,
    period_days: int = 30,
    now: datetime | None = None,
) -> AdminServiceQualitySummary:
    current_time = now or datetime.utcnow()
    cutoff = current_time - timedelta(days=period_days)
    feedback_rows = list((await db.execute(_summary_query(cutoff, current_time))).all())

    consultant_ids = sorted(
        {
            consultant_id
            for row in feedback_rows
            if row.service_request_id is not None
            for consultant_id in (
                row.assigned_consultant_id,
                row.assigned_mingli_consultant_id,
                row.assigned_psychology_consultant_id,
            )
            if consultant_id is not None
        }
    )
    consultant_names = {}
    if consultant_ids:
        consultant_rows = (
            await db.execute(
                select(User.id, User.name).where(User.id.in_(consultant_ids))
            )
        ).all()
        consultant_names = {row.id: row.name for row in consultant_rows}

    rows_by_service = defaultdict(list)
    rows_by_specialty = defaultdict(list)
    rows_by_consultant = defaultdict(list)
    rows_by_week = defaultdict(list)
    for row in feedback_rows:
        service_key = "report" if row.service_request_id is not None else "calendar"
        rows_by_service[service_key].append(row)
        if service_key == "report":
            rows_by_specialty[_specialty_key(row.consultation_type)].append(row)
            specialty_consultants = {
                row.assigned_mingli_consultant_id,
                row.assigned_psychology_consultant_id,
            } - {None}
            responsible_consultants = specialty_consultants or {
                row.assigned_consultant_id
            } - {None}
            for consultant_id in responsible_consultants:
                rows_by_consultant[consultant_id].append(row)
        rows_by_week[_weekly_start(row.created_at.date())].append(row)

    weekly_trend = []
    week = _weekly_start(cutoff.date())
    final_week = _weekly_start(current_time.date())
    while week <= final_week:
        metrics = _quality_metrics(rows_by_week.get(week, []))
        weekly_trend.append(
            {
                "week_start": week,
                "feedback_count": metrics["feedback_count"],
                "rated_count": metrics["rated_count"],
                "average_rating": metrics["average_rating"],
                "complaint_count": metrics["complaint_count"],
            }
        )
        week += timedelta(days=7)

    return AdminServiceQualitySummary(
        period_days=period_days,
        range_start=cutoff.date(),
        range_end=current_time.date(),
        totals=_quality_metrics(feedback_rows),
        by_service=[
            {
                "key": key,
                "label": SERVICE_LABELS[key],
                **_quality_metrics(rows_by_service.get(key, [])),
            }
            for key in SERVICE_LABELS
        ],
        by_specialty=[
            {
                "key": key,
                "label": label,
                **_quality_metrics(rows_by_specialty.get(key, [])),
            }
            for key, label in SPECIALTY_LABELS.items()
        ],
        by_consultant=[
            {
                "consultant_id": consultant_id,
                "consultant_name": consultant_names.get(
                    consultant_id, f"咨询师 #{consultant_id}"
                ),
                **_consultant_rating_metrics(rows),
            }
            for consultant_id, rows in sorted(
                rows_by_consultant.items(),
                key=lambda item: (-len(item[1]), item[0]),
            )
        ],
        weekly_trend=weekly_trend,
    )
