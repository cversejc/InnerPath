"""Consultant access, queue, workspace, and response serialization."""

from copy import deepcopy
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ServiceRequest, ServiceRequestTask
from app.models.user import User
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from .repository import _get_draft, _get_latest_task, _get_request_for_update
from app.domains.workflow.authorization import (
    SPECIALTY_FIELDS,
    assignment_condition,
    consultant_capabilities,
    is_assigned,
)
from app.domains.workflow.models import ReportCase, StepTask


STALE_SERVICE_REQUEST_STATUSES = ("accepted", "ai_processing", "ai_ready", "reviewing")
WORKFLOW_ACTIVE_STEP_STATUSES = (
    "READY",
    "EXECUTING",
    "WAITING_REVIEW",
    "IN_REVIEW",
    "NEEDS_REVISION",
)


def workflow_attention_condition(now: Optional[datetime] = None):
    cutoff = (now or datetime.utcnow()) - timedelta(hours=24)
    case_conditions = (
        ReportCase.service_request_id == ServiceRequest.id,
        ReportCase.status.in_(("ACTIVE", "READY_TO_DELIVER")),
        ServiceRequest.service_type == "report",
        ServiceRequest.status.not_in(("needs_info", "delivered", "withdrawn", "rejected")),
    )
    failed_step = (
        select(StepTask.id)
        .join(ReportCase, ReportCase.workflow_instance_id == StepTask.workflow_instance_id)
        .where(*case_conditions, StepTask.status == "FAILED")
        .exists()
    )
    stale_step = (
        select(StepTask.id)
        .join(ReportCase, ReportCase.workflow_instance_id == StepTask.workflow_instance_id)
        .where(
            *case_conditions,
            StepTask.status.in_(WORKFLOW_ACTIVE_STEP_STATUSES),
            StepTask.updated_at < cutoff,
        )
        .exists()
    )
    return and_(ServiceRequest.service_type == "report", or_(failed_step, stale_step))


def assignment_incomplete_condition():
    collaborative = select(ReportCase.id).where(
        ReportCase.service_request_id == ServiceRequest.id,
        ReportCase.application_snapshot["collaboration_contract"].is_not(None),
    ).exists()
    collaborative_assignment_missing = or_(
        and_(
            ServiceRequest.consultation_type == "metaphysics",
            ServiceRequest.assigned_mingli_consultant_id.is_(None),
        ),
        and_(
            ServiceRequest.consultation_type == "psychology",
            ServiceRequest.assigned_psychology_consultant_id.is_(None),
        ),
        and_(
            ServiceRequest.consultation_type == "integrated",
            or_(
                ServiceRequest.assigned_mingli_consultant_id.is_(None),
                ServiceRequest.assigned_psychology_consultant_id.is_(None),
            ),
        ),
        ServiceRequest.consultation_type.is_(None),
        ServiceRequest.consultation_type.not_in(("metaphysics", "psychology", "integrated")),
    )
    return or_(
        and_(~collaborative, ServiceRequest.assigned_consultant_id.is_(None)),
        and_(collaborative, collaborative_assignment_missing),
    )


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
        capabilities = consultant_capabilities(consultant)
        if service_request.consultation_type == "metaphysics":
            capabilities.intersection_update({"mingli"})
        elif service_request.consultation_type == "psychology":
            capabilities.intersection_update({"psychology"})
        if not capabilities or consultant.role != "consultant" or not consultant.is_active:
            raise ValueError("consultant_specialty_required")
        if service_request.status in {"withdrawn", "rejected", "delivered"}:
            raise ValueError("service_request_read_only")

        tasks = list(await db.scalars(select(StepTask).where(
            StepTask.workflow_instance_id == case.workflow_instance_id,
            StepTask.required_capability.in_(capabilities),
        ).with_for_update()))
        claimed = []
        for specialty in capabilities:
            field = SPECIALTY_FIELDS[specialty]
            assigned = getattr(service_request, field)
            if assigned not in (None, consultant.id):
                continue
            specialty_tasks = [task for task in tasks if task.required_capability == specialty]
            if not specialty_tasks:
                continue
            if any(task.status == "COMPLETED" and task.assignee_id != consultant.id for task in specialty_tasks):
                continue
            setattr(service_request, field, consultant.id)
            for task in specialty_tasks:
                task.assignee_id = consultant.id
            claimed.append(specialty)
        if not claimed:
            raise ValueError("service_request_already_taken")
        service_request.assigned_consultant_id = service_request.assigned_consultant_id or consultant.id
        if service_request.status == "submitted":
            service_request.status = "accepted"
        service_request.accepted_at = service_request.accepted_at or datetime.utcnow()
        service_request.updated_by = consultant.id
        await record_audit(db, consultant.id, "service_request.specialty.accept", "service_request",
                           str(request_id), target_user_id=service_request.user_id,
                           details={"specialties": sorted(claimed)}, audit_context=audit_context)
        await db.commit()
        await db.refresh(service_request)
        return service_request
    if service_request.status == "accepted" and service_request.assigned_consultant_id == consultant.id:
        return service_request
    if service_request.status != "submitted" or service_request.assigned_consultant_id is not None:
        raise ValueError("service_request_already_taken")
    if not consultant_can_cover_specialty(consultant, service_request.consultation_type):
        raise ValueError("consultant_specialty_mismatch")
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


def consultant_can_cover_specialty(consultant: User, consultation_type: Optional[str]) -> bool:
    if consultation_type is None:
        return True
    specialties = set(consultant.consultant_specialties or [])
    consultant_type = getattr(consultant, "consultant_type", None)
    if consultant_type == "mingli":
        specialties.add("metaphysics")
    elif consultant_type == "psychology":
        specialties.add("psychology")
    elif consultant_type == "integrated":
        specialties.update({"metaphysics", "psychology"})
    if consultation_type == "integrated":
        return {"metaphysics", "psychology"}.issubset(specialties)
    return consultation_type in specialties


def consultant_request_types(consultant: User) -> list[str]:
    specialties = set(consultant.consultant_specialties or [])
    consultant_type = getattr(consultant, "consultant_type", None)
    if consultant_type == "mingli":
        specialties.add("metaphysics")
    elif consultant_type == "psychology":
        specialties.add("psychology")
    elif consultant_type == "integrated":
        specialties.update({"metaphysics", "psychology"})
    supported = specialties & {"metaphysics", "psychology"}
    if {"metaphysics", "psychology"}.issubset(specialties):
        supported.add("integrated")
    return sorted(supported)


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
    collaborative = select(ReportCase.id).join(
        StepTask, StepTask.workflow_instance_id == ReportCase.workflow_instance_id
    ).where(
        ReportCase.service_request_id == ServiceRequest.id,
        StepTask.required_capability.in_(SPECIALTY_FIELDS),
    ).exists()
    if user.role != "admin":
        if scope == "available":
            supported_types = consultant_request_types(user)
            capabilities = consultant_capabilities(user)
            legacy_direction = (
                or_(
                    ServiceRequest.consultation_type.is_(None),
                    ServiceRequest.consultation_type.in_(supported_types),
                )
                if supported_types
                else false()
            )
            legacy_available = and_(
                ~collaborative,
                ServiceRequest.status == "submitted",
                ServiceRequest.assigned_consultant_id.is_(None),
                legacy_direction,
            )
            collaborative_available = []
            for capability in capabilities:
                has_capability_step = select(ReportCase.id).join(
                    StepTask,
                    StepTask.workflow_instance_id == ReportCase.workflow_instance_id,
                ).where(
                    ReportCase.service_request_id == ServiceRequest.id,
                    StepTask.required_capability == capability,
                ).exists()
                collaborative_available.append(
                    and_(
                        has_capability_step,
                        getattr(ServiceRequest, SPECIALTY_FIELDS[capability]).is_(None),
                    )
                )
            query = query.where(
                ServiceRequest.status.not_in(("withdrawn", "rejected", "delivered")),
                or_(*(collaborative_available + [legacy_available]))
                if collaborative_available
                else legacy_available,
            )
        else:
            query = query.where(assignment_condition(user.id), ServiceRequest.status.not_in(("withdrawn", "rejected")))
    elif scope == "available":
        legacy_available = and_(
            ~collaborative,
            ServiceRequest.status == "submitted",
            ServiceRequest.assigned_consultant_id.is_(None),
        )
        collaborative_available = []
        for specialty, field in SPECIALTY_FIELDS.items():
            has_capability_step = select(ReportCase.id).join(
                StepTask,
                StepTask.workflow_instance_id == ReportCase.workflow_instance_id,
            ).where(
                ReportCase.service_request_id == ServiceRequest.id,
                StepTask.required_capability == specialty,
            ).exists()
            collaborative_available.append(
                and_(has_capability_step, getattr(ServiceRequest, field).is_(None))
            )
        query = query.where(
            ServiceRequest.status.not_in(("withdrawn", "rejected", "delivered")),
            or_(*(collaborative_available + [legacy_available])),
        )
    elif scope == "mine":
        query = query.where(assignment_condition(user.id))
    if status:
        query = query.where(ServiceRequest.status == status)
    if service_type:
        query = query.where(ServiceRequest.service_type == service_type)
    result = await db.execute(query.order_by(ServiceRequest.created_at.desc()))
    return list(result.all())


async def list_admin_service_requests(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
    user_id: Optional[int] = None,
    consultant_id: Optional[int] = None,
    queue_filter: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[tuple[ServiceRequest, User, Optional[User], Optional[User], Optional[User]]], int]:
    conditions = []
    if queue_filter in {"incomplete_assignment", "incomplete_assignment_over_24h"}:
        conditions.extend((
            ServiceRequest.status.not_in(("delivered", "withdrawn", "rejected")),
            assignment_incomplete_condition(),
        ))
        if queue_filter == "incomplete_assignment_over_24h":
            conditions.append(ServiceRequest.created_at < datetime.utcnow() - timedelta(hours=24))
    elif queue_filter == "stale_over_24h":
        conditions.extend((
            ServiceRequest.status.in_(STALE_SERVICE_REQUEST_STATUSES),
            ServiceRequest.updated_at < datetime.utcnow() - timedelta(hours=24),
            ~select(ReportCase.id)
            .where(ReportCase.service_request_id == ServiceRequest.id)
            .exists(),
        ))
    elif queue_filter == "workflow_attention":
        conditions.append(workflow_attention_condition())
    if status:
        conditions.append(ServiceRequest.status == status)
    if service_type:
        conditions.append(ServiceRequest.service_type == service_type)
    if user_id:
        conditions.append(ServiceRequest.user_id == user_id)
    if consultant_id:
        conditions.append(
            or_(
                ServiceRequest.assigned_consultant_id == consultant_id,
                ServiceRequest.assigned_mingli_consultant_id == consultant_id,
                ServiceRequest.assigned_psychology_consultant_id == consultant_id,
            )
        )
    if date_from:
        conditions.append(ServiceRequest.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        conditions.append(ServiceRequest.created_at < datetime.combine(date_to + timedelta(days=1), time.min))
    if search:
        term = f"%{search.strip()}%"
        conditions.append(or_(User.name.ilike(term), User.phone.ilike(term)))

    count_query = select(func.count(ServiceRequest.id)).join(User, User.id == ServiceRequest.user_id)
    consultant = aliased(User)
    mingli_consultant = aliased(User)
    psychology_consultant = aliased(User)
    query = select(ServiceRequest, User, consultant, mingli_consultant, psychology_consultant).join(
        User, User.id == ServiceRequest.user_id
    )
    query = query.outerjoin(consultant, consultant.id == ServiceRequest.assigned_consultant_id)
    query = query.outerjoin(
        mingli_consultant,
        mingli_consultant.id == ServiceRequest.assigned_mingli_consultant_id,
    ).outerjoin(
        psychology_consultant,
        psychology_consultant.id == ServiceRequest.assigned_psychology_consultant_id,
    )
    if conditions:
        count_query = count_query.where(*conditions)
        query = query.where(*conditions)

    total = int(await db.scalar(count_query) or 0)
    result = await db.execute(
        query.order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(result.all()), total

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
        "consultation_type": service_request.consultation_type,
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
