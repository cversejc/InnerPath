from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import String, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.domains.calendar.models import CalendarRequest
from app.domains.feedback.models import ServiceFeedback
from app.domains.feedback.schemas import (
    AdminServiceFeedbackItem,
    AdminServiceFeedbackUpdate,
    ServiceFeedbackCreate,
)
from app.domains.service_requests.models import ServiceRequest
from app.models.user import User


async def submit_service_feedback(
    db: AsyncSession,
    *,
    user: User,
    data: ServiceFeedbackCreate,
    audit_context: Optional[AuditContext] = None,
) -> ServiceFeedback:
    if (data.service_request_id is None) == (data.calendar_request_id is None):
        raise ValueError("feedback_target_invalid")

    if data.service_request_id is not None:
        request = await db.scalar(
            select(ServiceRequest)
            .where(
                ServiceRequest.id == data.service_request_id,
                ServiceRequest.user_id == user.id,
            )
            .with_for_update()
        )
        if request is None:
            raise ValueError("feedback_target_not_found")
        if (
            request.service_type != "report"
            or request.status != "delivered"
            or request.result_type != "report"
        ):
            raise ValueError("feedback_target_not_delivered")
        target_filter = ServiceFeedback.service_request_id == request.id
        target_type = "report"
        target_id = request.id
    else:
        calendar_request = await db.scalar(
            select(CalendarRequest)
            .where(
                CalendarRequest.id == data.calendar_request_id,
                CalendarRequest.user_id == user.id,
            )
            .with_for_update()
        )
        if calendar_request is None:
            raise ValueError("feedback_target_not_found")
        if (
            calendar_request.status not in {"fulfilled", "delivered"}
            or calendar_request.calendar_id is None
        ):
            raise ValueError("feedback_target_not_delivered")
        target_filter = ServiceFeedback.calendar_request_id == calendar_request.id
        target_type = "calendar"
        target_id = calendar_request.id

    if await db.scalar(select(ServiceFeedback.id).where(target_filter)) is not None:
        raise ValueError("feedback_already_submitted")

    feedback = ServiceFeedback(
        user_id=user.id,
        service_request_id=data.service_request_id,
        calendar_request_id=data.calendar_request_id,
        feedback_type=data.feedback_type,
        rating=data.rating,
        comment=data.comment,
        status="NEW",
    )
    db.add(feedback)
    await db.flush()
    await record_audit(
        db,
        actor_user_id=user.id,
        action="service_feedback.submit",
        resource_type="service_feedback",
        resource_id=str(feedback.id),
        target_user_id=user.id,
        details={
            "service_type": target_type,
            "target_id": target_id,
            "feedback_type": data.feedback_type,
            "rating": data.rating,
        },
        audit_context=audit_context,
    )
    return feedback


async def list_my_service_feedback(
    db: AsyncSession, user_id: int
) -> list[ServiceFeedback]:
    return list(
        await db.scalars(
            select(ServiceFeedback)
            .where(ServiceFeedback.user_id == user_id)
            .order_by(ServiceFeedback.created_at.desc(), ServiceFeedback.id.desc())
        )
    )


def _admin_feedback_filters(
    *,
    status: Optional[str],
    feedback_type: Optional[str],
    service_type: Optional[str],
    search: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
):
    conditions = []
    if status:
        conditions.append(ServiceFeedback.status == status)
    if feedback_type:
        conditions.append(ServiceFeedback.feedback_type == feedback_type)
    if service_type == "report":
        conditions.append(ServiceFeedback.service_request_id.is_not(None))
    elif service_type == "calendar":
        conditions.append(ServiceFeedback.calendar_request_id.is_not(None))
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                User.name.ilike(pattern),
                User.phone.ilike(pattern),
                ServiceFeedback.comment.ilike(pattern),
                cast(ServiceFeedback.id, String).ilike(pattern),
                cast(ServiceFeedback.service_request_id, String).ilike(pattern),
                cast(ServiceFeedback.calendar_request_id, String).ilike(pattern),
            )
        )
    if date_from:
        conditions.append(
            ServiceFeedback.created_at >= datetime.combine(date_from, time.min)
        )
    if date_to:
        conditions.append(
            ServiceFeedback.created_at < datetime.combine(date_to + timedelta(days=1), time.min)
        )
    return conditions


async def list_admin_service_feedback(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    feedback_type: Optional[str] = None,
    service_type: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[AdminServiceFeedbackItem], int]:
    conditions = _admin_feedback_filters(
        status=status,
        feedback_type=feedback_type,
        service_type=service_type,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    joins = (
        select(ServiceFeedback, User, ServiceRequest, CalendarRequest)
        .join(User, User.id == ServiceFeedback.user_id)
        .outerjoin(ServiceRequest, ServiceRequest.id == ServiceFeedback.service_request_id)
        .outerjoin(CalendarRequest, CalendarRequest.id == ServiceFeedback.calendar_request_id)
    )
    total = await db.scalar(
        select(func.count(ServiceFeedback.id))
        .select_from(ServiceFeedback)
        .join(User, User.id == ServiceFeedback.user_id)
        .outerjoin(ServiceRequest, ServiceRequest.id == ServiceFeedback.service_request_id)
        .outerjoin(CalendarRequest, CalendarRequest.id == ServiceFeedback.calendar_request_id)
        .where(*conditions)
    )
    result = await db.execute(
        joins.where(*conditions)
        .order_by(
            case(
                (ServiceFeedback.status == "NEW", 0),
                (ServiceFeedback.status == "IN_PROGRESS", 1),
                else_=2,
            ),
            ServiceFeedback.created_at.desc(),
            ServiceFeedback.id.desc(),
        )
        .offset((page - 1) * size)
        .limit(size)
    )
    items = []
    for feedback, user, service_request, calendar_request in result.all():
        items.append(
            AdminServiceFeedbackItem(
                id=feedback.id,
                user_id=user.id,
                user_name=user.name,
                user_phone=user.phone,
                service_type="report" if service_request else "calendar",
                service_request_id=feedback.service_request_id,
                calendar_request_id=feedback.calendar_request_id,
                service_result_id=(
                    service_request.result_id if service_request else calendar_request.calendar_id
                ),
                source_status=(
                    service_request.status if service_request else calendar_request.status
                ),
                feedback_type=feedback.feedback_type,
                rating=feedback.rating,
                comment=feedback.comment,
                status=feedback.status,
                assigned_to=feedback.assigned_to,
                resolution=feedback.resolution,
                resolved_by=feedback.resolved_by,
                resolved_at=feedback.resolved_at,
                created_at=feedback.created_at,
                updated_at=feedback.updated_at,
            )
        )
    return items, int(total or 0)


async def update_admin_service_feedback(
    db: AsyncSession,
    *,
    feedback_id: int,
    actor: User,
    data: AdminServiceFeedbackUpdate,
    audit_context: Optional[AuditContext] = None,
) -> ServiceFeedback:
    feedback = await db.scalar(
        select(ServiceFeedback)
        .where(ServiceFeedback.id == feedback_id)
        .with_for_update()
    )
    if feedback is None:
        raise ValueError("feedback_not_found")
    if data.status == "RESOLVED" and not data.resolution:
        raise ValueError("feedback_resolution_required")

    if data.assigned_to is not None:
        assignee = await db.scalar(
            select(User).where(
                User.id == data.assigned_to,
                User.role == "admin",
                User.is_active.is_(True),
            )
        )
        if assignee is None:
            raise ValueError("feedback_assignee_invalid")

    previous_status = feedback.status
    previous_assignee = feedback.assigned_to
    feedback.status = data.status
    feedback.assigned_to = data.assigned_to
    feedback.updated_by = actor.id
    if data.status == "RESOLVED":
        resolution_changed = feedback.resolution != data.resolution
        feedback.resolution = data.resolution
        if previous_status != "RESOLVED" or resolution_changed:
            feedback.resolved_by = actor.id
            feedback.resolved_at = datetime.utcnow()
    else:
        feedback.resolution = None
        feedback.resolved_by = None
        feedback.resolved_at = None

    await db.flush()
    await record_audit(
        db,
        actor_user_id=actor.id,
        action="service_feedback.update",
        resource_type="service_feedback",
        resource_id=str(feedback.id),
        target_user_id=feedback.user_id,
        details={
            "from_status": previous_status,
            "to_status": feedback.status,
            "from_assigned_to": previous_assignee,
            "assigned_to": feedback.assigned_to,
            "resolved": feedback.status == "RESOLVED",
        },
        audit_context=audit_context,
    )
    return feedback
