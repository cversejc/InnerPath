"""Consultant access, queue, workspace, and response serialization."""

from copy import deepcopy
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ServiceRequest, ServiceRequestTask
from app.models.user import User
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from .repository import _get_draft, _get_latest_task, _get_request_for_update


async def accept_service_request(
    db: AsyncSession,
    request_id: int,
    consultant: User,
    audit_context: Optional[AuditContext] = None,
) -> ServiceRequest:
    service_request = await _get_request_for_update(db, request_id)
    if service_request is None:
        raise ValueError("service_request_not_found")
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
    return user.role == "admin" or service_request.assigned_consultant_id == user.id


async def has_staff_assignment(db: AsyncSession, staff_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(ServiceRequest.id)
        .where(
            ServiceRequest.user_id == user_id,
            ServiceRequest.assigned_consultant_id == staff_id,
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
    if user.role != "admin":
        if scope == "available":
            query = query.where(
                ServiceRequest.status == "submitted",
                ServiceRequest.assigned_consultant_id.is_(None),
            )
        else:
            query = query.where(ServiceRequest.assigned_consultant_id == user.id)
    elif scope == "available":
        query = query.where(
            ServiceRequest.status == "submitted",
            ServiceRequest.assigned_consultant_id.is_(None),
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
