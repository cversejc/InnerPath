"""Admin read model for consultant load and consultant-performed work events."""

from datetime import datetime, timedelta
from statistics import median, quantiles

from sqlalchemy import String, case, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.models import AuditLog
from app.domains.service_requests.models import ServiceRequest
from app.domains.service_requests.staff import STALE_SERVICE_REQUEST_STATUSES
from app.domains.workflow.models import ReportCase
from app.models.user import User


CLOSED_REQUEST_STATUSES = ("delivered", "withdrawn", "rejected")
ACCEPT_ACTIONS = ("service_request.accept", "service_request.specialty.accept")
STALE_REQUEST_HOURS = 24
ACTIVE_REQUEST_PREVIEW_LIMIT = 5
ACTIVE_REQUEST_STATUS_ORDER = (
    "submitted",
    "accepted",
    "ai_processing",
    "ai_ready",
    "reviewing",
    "needs_info",
    "failed",
)


def consultant_active_status_counts(consultant_ids):
    assignments = consultant_request_assignments()
    return (
        select(
            assignments.c.consultant_id,
            ServiceRequest.status,
            func.count(ServiceRequest.id).label("request_count"),
        )
        .join(ServiceRequest, ServiceRequest.id == assignments.c.request_id)
        .where(
            assignments.c.consultant_id.in_(consultant_ids),
            ServiceRequest.status.not_in(CLOSED_REQUEST_STATUSES),
        )
        .group_by(assignments.c.consultant_id, ServiceRequest.status)
    )


def consultant_delivered_request_cycles(consultant_ids, *, cutoff):
    assignments = consultant_request_assignments()
    return (
        select(
            assignments.c.consultant_id,
            ServiceRequest.created_at,
            ServiceRequest.delivered_at,
        )
        .join(ServiceRequest, ServiceRequest.id == assignments.c.request_id)
        .where(
            assignments.c.consultant_id.in_(consultant_ids),
            ServiceRequest.service_type == "report",
            ServiceRequest.status == "delivered",
            ServiceRequest.delivered_at >= cutoff,
            ServiceRequest.created_at.is_not(None),
        )
    )


def summarize_delivery_cycles(hours: list[float]) -> dict:
    ordered = sorted(value for value in hours if value >= 0)
    if not ordered:
        return {
            "delivered_cycle_samples": 0,
            "delivery_cycle_p50_hours": None,
            "delivery_cycle_p90_hours": None,
        }
    p90 = quantiles(ordered, n=10, method="inclusive")[8] if len(ordered) > 1 else ordered[0]
    return {
        "delivered_cycle_samples": len(ordered),
        "delivery_cycle_p50_hours": round(median(ordered), 1),
        "delivery_cycle_p90_hours": round(p90, 1),
    }


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


def consultant_specialty_request_assignments():
    assignments = union_all(
        select(
            ServiceRequest.assigned_consultant_id.label("consultant_id"),
            literal("mingli").label("specialty"),
            ServiceRequest.id.label("request_id"),
        ).where(
            ServiceRequest.service_type == "report",
            ServiceRequest.assigned_consultant_id.is_not(None),
            ServiceRequest.consultation_type.in_(("metaphysics", "integrated")),
        ),
        select(
            ServiceRequest.assigned_consultant_id.label("consultant_id"),
            literal("psychology").label("specialty"),
            ServiceRequest.id.label("request_id"),
        ).where(
            ServiceRequest.service_type == "report",
            ServiceRequest.assigned_consultant_id.is_not(None),
            ServiceRequest.consultation_type.in_(("psychology", "integrated")),
        ),
        select(
            ServiceRequest.assigned_mingli_consultant_id.label("consultant_id"),
            literal("mingli").label("specialty"),
            ServiceRequest.id.label("request_id"),
        ).where(
            ServiceRequest.service_type == "report",
            ServiceRequest.assigned_mingli_consultant_id.is_not(None),
        ),
        select(
            ServiceRequest.assigned_psychology_consultant_id.label("consultant_id"),
            literal("psychology").label("specialty"),
            ServiceRequest.id.label("request_id"),
        ).where(
            ServiceRequest.service_type == "report",
            ServiceRequest.assigned_psychology_consultant_id.is_not(None),
        ),
    ).subquery("consultant_specialty_request_slots")
    return select(
        assignments.c.consultant_id,
        assignments.c.specialty,
        assignments.c.request_id,
    ).distinct().subquery("consultant_specialty_request_assignments")


def consultant_specialty_load_counts(consultant_ids, *, stale_cutoff):
    assignments = consultant_specialty_request_assignments()
    return (
        select(
            assignments.c.consultant_id,
            assignments.c.specialty,
            func.sum(
                case(
                    (
                        ServiceRequest.status.not_in(CLOSED_REQUEST_STATUSES),
                        1,
                    ),
                    else_=0,
                )
            ).label("active_requests"),
            func.sum(
                case(
                    (
                        ServiceRequest.status.in_(STALE_SERVICE_REQUEST_STATUSES)
                        & (ServiceRequest.updated_at < stale_cutoff),
                        1,
                    ),
                    else_=0,
                )
            ).label("stale_active_requests"),
        )
        .join(ServiceRequest, ServiceRequest.id == assignments.c.request_id)
        .where(assignments.c.consultant_id.in_(consultant_ids))
        .group_by(assignments.c.consultant_id, assignments.c.specialty)
    )


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


def consultant_active_request_preview(consultant_ids, *, limit=ACTIVE_REQUEST_PREVIEW_LIMIT):
    assignments = consultant_request_assignments()
    ranked_requests = (
        select(
            assignments.c.consultant_id,
            ServiceRequest.id.label("request_id"),
            ServiceRequest.user_id,
            User.name.label("user_name"),
            ServiceRequest.consultation_type,
            ServiceRequest.status.label("current_status"),
            ServiceRequest.created_at,
            ServiceRequest.updated_at,
            func.row_number()
            .over(
                partition_by=assignments.c.consultant_id,
                order_by=(
                    ServiceRequest.updated_at.asc(),
                    ServiceRequest.created_at.asc(),
                    ServiceRequest.id.asc(),
                ),
            )
            .label("request_rank"),
        )
        .join(ServiceRequest, ServiceRequest.id == assignments.c.request_id)
        .join(User, User.id == ServiceRequest.user_id)
        .where(
            assignments.c.consultant_id.in_(consultant_ids),
            ServiceRequest.status.not_in(CLOSED_REQUEST_STATUSES),
        )
        .subquery("ranked_consultant_active_requests")
    )
    return (
        select(ranked_requests)
        .where(ranked_requests.c.request_rank <= limit)
        .order_by(ranked_requests.c.consultant_id, ranked_requests.c.request_rank)
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
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(hours=STALE_REQUEST_HOURS)
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
                    func.sum(
                        case(
                            (
                                ServiceRequest.status.in_(STALE_SERVICE_REQUEST_STATUSES)
                                & (ServiceRequest.updated_at < stale_cutoff),
                                1,
                            ),
                            else_=0,
                        )
                    ).label("stale_active_requests"),
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
            "stale_active_requests": int(row.stale_active_requests or 0),
        }
        for row in assignment_rows
    }

    specialty_rows = list(
        (
            await db.execute(
                consultant_specialty_load_counts(
                    consultant_ids,
                    stale_cutoff=stale_cutoff,
                )
            )
        ).all()
    )
    specialty_loads = {}
    for row in specialty_rows:
        specialty_loads.setdefault(row.consultant_id, {})[row.specialty] = {
            "active_requests": int(row.active_requests or 0),
            "stale_active_requests": int(row.stale_active_requests or 0),
        }

    status_rows = list(
        (await db.execute(consultant_active_status_counts(consultant_ids))).all()
    )
    active_statuses_by_consultant = {}
    for row in status_rows:
        active_statuses_by_consultant.setdefault(row.consultant_id, []).append(
            {"status": row.status, "request_count": int(row.request_count or 0)}
        )
    status_order = {status: index for index, status in enumerate(ACTIVE_REQUEST_STATUS_ORDER)}
    for statuses in active_statuses_by_consultant.values():
        statuses.sort(key=lambda item: status_order.get(item["status"], len(status_order)))

    active_request_rows = list(
        (await db.execute(consultant_active_request_preview(consultant_ids))).all()
    )
    active_requests_by_consultant = {}
    for row in active_request_rows:
        active_requests_by_consultant.setdefault(row.consultant_id, []).append(
            {
                "request_id": row.request_id,
                "user_id": row.user_id,
                "user_name": row.user_name,
                "consultation_type": row.consultation_type,
                "current_status": row.current_status,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "age_hours": max(0, int((now - row.created_at).total_seconds() // 3600)),
                "idle_hours": max(0, int((now - row.updated_at).total_seconds() // 3600)),
                "is_stale": (
                    row.current_status in STALE_SERVICE_REQUEST_STATUSES
                    and row.updated_at < stale_cutoff
                ),
            }
        )

    cutoff = now - timedelta(days=period_days)
    delivery_cycle_rows = list(
        (
            await db.execute(
                consultant_delivered_request_cycles(consultant_ids, cutoff=cutoff)
            )
        ).all()
    )
    delivery_cycles_by_consultant = {}
    for row in delivery_cycle_rows:
        if row.created_at is None or row.delivered_at is None:
            continue
        duration = (row.delivered_at - row.created_at).total_seconds() / 3600
        if duration >= 0:
            delivery_cycles_by_consultant.setdefault(row.consultant_id, []).append(duration)

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
                    {
                        "total_requests": 0,
                        "active_requests": 0,
                        "stale_active_requests": 0,
                    },
                ),
                **event_counts.get(
                    consultant.id,
                    {"accepted_in_period": 0, "delivered_in_period": 0},
                ),
                "active_by_status": active_statuses_by_consultant.get(
                    consultant.id, []
                ),
                "specialty_load": [
                    {
                        "specialty": specialty,
                        **specialty_loads.get(consultant.id, {}).get(
                            specialty,
                            {"active_requests": 0, "stale_active_requests": 0},
                        ),
                    }
                    for specialty in ("mingli", "psychology")
                ],
                **summarize_delivery_cycles(
                    delivery_cycles_by_consultant.get(consultant.id, [])
                ),
                "active_request_preview": active_requests_by_consultant.get(
                    consultant.id, []
                ),
                "recent_events": recent_by_consultant.get(consultant.id, []),
            }
            for consultant in consultants
        ],
    }
