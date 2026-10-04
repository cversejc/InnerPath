"""Consultant access, queue, workspace, and response serialization."""

from copy import deepcopy
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ServiceRequest, ServiceRequestTask
from app.models.user import User
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from .repository import _get_draft, _get_latest_task, _get_request_for_update
from app.domains.workflow.authorization import assignment_condition, is_assigned, SPECIALTY_FIELDS
from app.domains.workflow.models import ReportCase, StepTask


async def accept_service_request(
    db: AsyncSession,
    request_id: int,
    consultant: User,
    audit_context: Optional[AuditContext] = None,
) -> ServiceRequest:
    service_request = await _get_request_for_update(db, request_id)
    if service_request is None:
        raise ValueError("service_request_not_found")
    if service_request.service_type == "calendar":
        raise ValueError("calendar_requires_delivered_report")
    case = await db.scalar(select(ReportCase).where(ReportCase.service_request_id == request_id))
    if case and (case.application_snapshot or {}).get("collaboration_contract"):
        specialty = getattr(consultant, "consultant_type", None)
        if specialty not in SPECIALTY_FIELDS or consultant.role != "consultant" or not consultant.is_active:
            raise ValueError("consultant_specialty_required")
        field = SPECIALTY_FIELDS[specialty]
        if service_request.status in {"withdrawn", "rejected", "delivered"}:
            raise ValueError("service_request_read_only")
        assigned = getattr(service_request, field)
        if assigned not in (None, consultant.id):
            raise ValueError("service_request_already_taken")
        setattr(service_request, field, consultant.id)
        service_request.assigned_consultant_id = service_request.assigned_consultant_id or consultant.id
        tasks = await db.scalars(select(StepTask).where(
            StepTask.workflow_instance_id == case.workflow_instance_id,
            StepTask.required_capability == specialty,
        ).with_for_update())
        for task in tasks:
            if task.status == "COMPLETED" and task.assignee_id != consultant.id:
                raise ValueError("service_request_read_only")
            task.assignee_id = consultant.id
        if service_request.status == "submitted":
            service_request.status = "accepted"
        service_request.accepted_at = service_request.accepted_at or datetime.utcnow()
        service_request.updated_by = consultant.id
        await record_audit(db, consultant.id, "service_request.specialty.accept", "service_request",
                           str(request_id), target_user_id=service_request.user_id,
                           details={"specialty": specialty}, audit_context=audit_context)
        await db.commit()
        await db.refresh(service_request)
        return service_request
    if service_request.status == "accepted" and service_request.assigned_consultant_id == consultant.id:
        return service_request
    if service_request.status != "submitted" or service_request.assigned_consultant_id is not None:
        raise ValueError("service_request_already_taken")
    service_request.assigned_consultant_id = consultant.id
    service_request.status = "accepted"
    service_request.accepted_at = datetime.utcnow()
    service_request.updated_by = consultant.id
    await record_audit(
        db,
        consultant.id,
        "service_request.accept",
        "service_request",
        str(request_id),
        target_user_id=service_request.user_id,
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request

def staff_can_access(service_request: ServiceRequest, user: User) -> bool:
    return service_request.service_type != "calendar" and (
        getattr(service_request, "status", None) not in {"withdrawn", "rejected"}
        and (user.role == "admin" or is_assigned(service_request, user.id))
    )


async def has_staff_assignment(db: AsyncSession, staff_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(ServiceRequest.id)
        .where(
            ServiceRequest.user_id == user_id,
            assignment_condition(staff_id),
            ServiceRequest.status.not_in(("withdrawn", "rejected")),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def list_staff_service_requests(
    db: AsyncSession,
    user: User,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
    scope: str = "mine",
) -> list[tuple[ServiceRequest, Optional[User]]]:
    query = select(ServiceRequest, User).join(User, User.id == ServiceRequest.user_id)
    query = query.where(ServiceRequest.service_type == "report")
    collaborative = select(ReportCase.id).join(StepTask, StepTask.workflow_instance_id == ReportCase.workflow_instance_id).where(
        ReportCase.service_request_id == ServiceRequest.id,
        StepTask.required_capability.in_(SPECIALTY_FIELDS),
    ).exists()
    legacy_available = and_(~collaborative, ServiceRequest.status == "submitted", ServiceRequest.assigned_consultant_id.is_(None))
    if user.role != "admin":
        if scope == "available":
            field = SPECIALTY_FIELDS.get(getattr(user, "consultant_type", None))
            query = query.where(
                ServiceRequest.status.not_in(("withdrawn", "rejected", "delivered")),
                or_(and_(collaborative, getattr(ServiceRequest, field).is_(None)), legacy_available) if field else legacy_available,
            )
        else:
            query = query.where(assignment_condition(user.id), ServiceRequest.status.not_in(("withdrawn", "rejected")))
    elif scope == "available":
        query = query.where(
            ServiceRequest.status.not_in(("withdrawn", "rejected", "delivered")),
            or_(and_(collaborative, or_(ServiceRequest.assigned_mingli_consultant_id.is_(None), ServiceRequest.assigned_psychology_consultant_id.is_(None))), legacy_available),
        )
    elif scope == "mine":
        query = query.where(ServiceRequest.assigned_consultant_id == user.id)
    if status:
        query = query.where(ServiceRequest.status == status)
    if service_type:
        query = query.where(ServiceRequest.service_type == service_type)
    result = await db.execute(query.order_by(ServiceRequest.created_at.desc()))
    return list(result.all())

async def get_workspace(
    db: AsyncSession,
    service_request: ServiceRequest,
) -> dict[str, Any]:
    user = await db.get(User, service_request.user_id)
    consultant_name = None
    if service_request.assigned_consultant_id:
        consultant_name = await db.scalar(
            select(User.name).where(User.id == service_request.assigned_consultant_id)
        )
    draft = await _get_draft(db, service_request.id)
    task = await _get_latest_task(db, service_request.id)
    return {
        "request": serialize_service_request(service_request, consultant_name=consultant_name),
        "user": serialize_staff_user(user),
        "draft": draft,
        "task": task,
    }

def serialize_staff_user(user: Optional[User]) -> dict[str, Any]:
    if user is None:
        return {}
    return {
        "id": user.id,
        "name": user.name,
        "phone": user.phone,
        "gender": user.gender,
        "birth_year": user.birth_year,
        "birth_month": user.birth_month,
        "birth_day": user.birth_day,
        "birth_hour": user.birth_hour,
        "birth_minute": user.birth_minute,
        "birth_place": user.birth_place,
        "role": user.role,
    }

def serialize_service_request(
    service_request: ServiceRequest,
    consultant_name: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "id": service_request.id,
        "service_type": service_request.service_type,
        "status": service_request.status,
        "request_payload": deepcopy(service_request.request_payload or {}),
        "result_type": service_request.result_type,
        "result_id": service_request.result_id,
        "assigned_consultant_id": service_request.assigned_consultant_id,
        "assigned_mingli_consultant_id": service_request.assigned_mingli_consultant_id,
        "assigned_psychology_consultant_id": service_request.assigned_psychology_consultant_id,
        "needs_info_reason": service_request.needs_info_reason,
        "rejection_reason": service_request.rejection_reason,
        "last_error": service_request.last_error,
        "assigned_consultant_name": consultant_name,
        "created_at": service_request.created_at,
        "updated_at": service_request.updated_at,
        "accepted_at": service_request.accepted_at,
        "ai_started_at": service_request.ai_started_at,
        "ai_completed_at": service_request.ai_completed_at,
        "reviewing_at": service_request.reviewing_at,
        "needs_info_at": service_request.needs_info_at,
        "failed_at": service_request.failed_at,
        "delivered_at": service_request.delivered_at,
        "withdrawn_at": service_request.withdrawn_at,
        "rejected_at": service_request.rejected_at,
    }

def serialize_task(task: Optional[ServiceRequestTask]) -> Optional[dict[str, Any]]:
    if task is None:
        return None
    return {
        "task_id": task.task_id,
        "request_id": task.request_id,
        "service_type": task.service_type,
        "status": task.status,
        "progress": task.progress,
        "error": task.error,
        "retry_count": task.retry_count,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
