"""Admin read model for consultant load and consultant-performed work events."""

from datetime import datetime, timedelta

from sqlalchemy import String, case, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.models import AuditLog
from app.domains.service_requests.models import ServiceRequest
from app.domains.workflow.models import ReportCase
from app.models.user import User


CLOSED_REQUEST_STATUSES = ("delivered", "withdrawn", "rejected")
ACCEPT_ACTIONS = ("service_request.accept", "service_request.specialty.accept")


def consultant_request_assignments():
    assignments = union_all(
        select(
            ServiceRequest.assigned_consultant_id.label("consultant_id"),
            ServiceRequest.id.label("request_id"),
        ).where(
            ServiceRequest.service_type == "report",
            ServiceRequest.assigned_consultant_id.is_not(None),
        ),
        select(
            ServiceRequest.assigned_mingli_consultant_id.label("consultant_id"),
            ServiceRequest.id.label("request_id"),
        ).where(
            ServiceRequest.service_type == "report",
            ServiceRequest.assigned_mingli_consultant_id.is_not(None),
        ),
        select(
            ServiceRequest.assigned_psychology_consultant_id.label("consultant_id"),
            ServiceRequest.id.label("request_id"),
        ).where(
            ServiceRequest.service_type == "report",
            ServiceRequest.assigned_psychology_consultant_id.is_not(None),
        ),
    ).subquery("consultant_request_slots")
    return select(
        assignments.c.consultant_id,
        assignments.c.request_id,
    ).distinct().subquery("consultant_request_assignments")


def consultant_work_events():
    accepted = select(
        AuditLog.actor_user_id.label("consultant_id"),
        ServiceRequest.id.label("request_id"),
        AuditLog.id.label("event_id"),
        literal("accepted").label("event_type"),
        AuditLog.created_at.label("event_at"),
    ).join(
        ServiceRequest,
        AuditLog.resource_id == cast(ServiceRequest.id, String),
    ).where(
        AuditLog.resource_type == "service_request",
        AuditLog.action.in_(ACCEPT_ACTIONS),
        ServiceRequest.service_type == "report",
    )
    request_deliveries = select(
        AuditLog.actor_user_id.label("consultant_id"),
        ServiceRequest.id.label("request_id"),
        AuditLog.id.label("event_id"),
        literal("delivered").label("event_type"),
        AuditLog.created_at.label("event_at"),
    ).join(
        ServiceRequest,
        AuditLog.resource_id == cast(ServiceRequest.id, String),
    ).where(
        AuditLog.resource_type == "service_request",
        AuditLog.action == "service_request.deliver",
        ServiceRequest.service_type == "report",
    )
    report_deliveries = select(
        AuditLog.actor_user_id.label("consultant_id"),
        ServiceRequest.id.label("request_id"),
        AuditLog.id.label("event_id"),
        literal("delivered").label("event_type"),
        AuditLog.created_at.label("event_at"),
    ).join(
        ReportCase,
        AuditLog.resource_id == cast(ReportCase.id, String),
    ).join(
        ServiceRequest,
        ServiceRequest.id == ReportCase.service_request_id,
    ).where(
        AuditLog.resource_type == "report_case",
        AuditLog.action == "report_case.deliver",
        ServiceRequest.service_type == "report",
    )
    return union_all(accepted, request_deliveries, report_deliveries).subquery(
        "consultant_work_events"
    )


async def get_admin_consultant_workload(
    db: AsyncSession,
    *,
    period_days: int = 30,
    recent_event_limit: int = 5,
) -> dict:
    consultants = list(
        await db.scalars(
            select(User).where(User.role == "consultant").order_by(User.id)
        )
    )
    if not consultants:
        return {"period_days": period_days, "items": []}

    consultant_ids = [consultant.id for consultant in consultants]
    assignments = consultant_request_assignments()
    assignment_rows = list(
        (
            await db.execute(
                select(
                    assignments.c.consultant_id,
                    func.count(ServiceRequest.id).label("total_requests"),
                    func.sum(
                        case(
                            (
                                ServiceRequest.status.not_in(CLOSED_REQUEST_STATUSES),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("active_requests"),
                )
                .join(ServiceRequest, ServiceRequest.id == assignments.c.request_id)
                .where(assignments.c.consultant_id.in_(consultant_ids))
                .group_by(assignments.c.consultant_id)
            )
        ).all()
    )
    assignment_counts = {
        row.consultant_id: {
            "total_requests": int(row.total_requests or 0),
            "active_requests": int(row.active_requests or 0),
        }
        for row in assignment_rows
    }

    cutoff = datetime.utcnow() - timedelta(days=period_days)
    events = consultant_work_events()
    event_count_rows = list(
        (
            await db.execute(
                select(
                    events.c.consultant_id,
                    func.sum(case((events.c.event_type == "accepted", 1), else_=0)).label(
                        "accepted_in_period"
                    ),
                    func.sum(case((events.c.event_type == "delivered", 1), else_=0)).label(
                        "delivered_in_period"
                    ),
                )
                .join(User, User.id == events.c.consultant_id)
                .where(
                    User.role == "consultant",
                    events.c.consultant_id.in_(consultant_ids),
                    events.c.event_at >= cutoff,
                )
                .group_by(events.c.consultant_id)
            )
        ).all()
    )
    event_counts = {
        row.consultant_id: {
            "accepted_in_period": int(row.accepted_in_period or 0),
            "delivered_in_period": int(row.delivered_in_period or 0),
        }
        for row in event_count_rows
    }

    ranked_events = (
        select(
            events.c.consultant_id,
            events.c.request_id,
            events.c.event_id,
            events.c.event_type,
            events.c.event_at,
            ServiceRequest.user_id,
            User.name.label("user_name"),
            ServiceRequest.consultation_type,
            ServiceRequest.status.label("current_status"),
            func.row_number()
            .over(
                partition_by=events.c.consultant_id,
                order_by=(events.c.event_at.desc(), events.c.event_id.desc()),
            )
            .label("event_rank"),
        )
        .join(ServiceRequest, ServiceRequest.id == events.c.request_id)
        .join(User, User.id == ServiceRequest.user_id)
        .where(
            events.c.consultant_id.in_(consultant_ids),
            ServiceRequest.service_type == "report",
        )
        .subquery("ranked_consultant_work_events")
    )
    recent_rows = list(
        (
            await db.execute(
                select(ranked_events)
                .where(ranked_events.c.event_rank <= recent_event_limit)
                .order_by(ranked_events.c.consultant_id, ranked_events.c.event_rank)
            )
        ).all()
    )
    recent_by_consultant = {}
    for row in recent_rows:
        recent_by_consultant.setdefault(row.consultant_id, []).append(
            {
                "request_id": row.request_id,
                "user_id": row.user_id,
                "user_name": row.user_name,
                "consultation_type": row.consultation_type,
                "current_status": row.current_status,
                "event_type": row.event_type,
                "event_at": row.event_at,
            }
        )

    return {
        "period_days": period_days,
        "items": [
            {
                "consultant_id": consultant.id,
                **assignment_counts.get(
                    consultant.id,
                    {"total_requests": 0, "active_requests": 0},
                ),
                **event_counts.get(
                    consultant.id,
                    {"accepted_in_period": 0, "delivered_in_period": 0},
                ),
                "recent_events": recent_by_consultant.get(consultant.id, []),
            }
            for consultant in consultants
        ],
    }
