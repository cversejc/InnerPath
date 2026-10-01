"""AI task and consultant review transitions for service requests."""

from copy import deepcopy
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ServiceRequest, ServiceRequestDraft, ServiceRequestTask
from app.models.user import User
from .schemas import ServiceRequestDraftUpdate, ServiceRequestInfoInput
from app.services.audit_service import record_audit
from .drafts import validate_draft
from .repository import (
    _append_revision,
    _get_draft,
    _get_draft_for_update,
    _get_latest_task,
    _get_request_for_update,
)
from .staff import staff_can_access


async def enqueue_ai_draft(
    db: AsyncSession,
    service_request: ServiceRequest,
    actor: User,
    request: Optional[Request] = None,
    *,
    force: bool = False,
    retry_of_task_id: Optional[str] = None,
) -> ServiceRequestTask:
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    allowed_statuses = {"accepted", "failed"}
    if force:
        allowed_statuses.update({"ai_ready", "reviewing"})
    if service_request.status not in allowed_statuses:
        raise ValueError("ai_draft_not_allowed")
    active = await db.scalar(
        select(ServiceRequestTask).where(
            ServiceRequestTask.request_id == service_request.id,
            ServiceRequestTask.status == "processing",
        )
    )
    if active:
        return active

    draft = await _get_draft(db, service_request.id)
    if force and draft:
        await _append_revision(db, service_request.id, "before_ai_regeneration", draft.editable_payload, actor.id)

    parent_task = None
    if retry_of_task_id is None:
        latest_task = await _get_latest_task(db, service_request.id)
        if latest_task and latest_task.status in {"failed", "completed"}:
            retry_of_task_id = latest_task.task_id
    if retry_of_task_id:
        parent_task = await db.get(ServiceRequestTask, retry_of_task_id)

    task_id = str(uuid4())
    task = ServiceRequestTask(
        task_id=task_id,
        request_id=service_request.id,
        service_type=service_request.service_type,
        status="processing",
        progress=0,
        input_snapshot=deepcopy(service_request.request_payload),
        retry_count=(parent_task.retry_count + 1) if parent_task else 0,
        retry_of_task_id=retry_of_task_id,
    )
    db.add(task)
    service_request.status = "ai_processing"
    service_request.ai_started_at = datetime.utcnow()
    service_request.failed_at = None
    service_request.last_error = None
    service_request.updated_by = actor.id
    await record_audit(
        db,
        actor.id,
        "service_request.ai.start",
        "service_request",
        str(service_request.id),
        target_user_id=service_request.user_id,
        details={"service_type": service_request.service_type, "task_id": task_id},
        request=request,
    )
    await db.commit()
    await db.refresh(task)

    from app.tasks.service_request_tasks import generate_service_request_task

    generate_service_request_task.apply_async(args=[service_request.id], task_id=task_id)
    return task


async def save_service_request_draft(
    db: AsyncSession,
    service_request: ServiceRequest,
    actor: User,
    data: ServiceRequestDraftUpdate,
    request: Optional[Request] = None,
) -> ServiceRequestDraft:
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    if service_request.status not in {"ai_ready", "reviewing"}:
        raise ValueError("draft_save_not_allowed")
    draft = await _get_draft_for_update(db, service_request.id)
    if draft is None:
        raise ValueError("service_request_draft_not_found")
    if data.expected_version is not None and data.expected_version != draft.content_version:
        raise ValueError("draft_version_conflict")
    normalized = validate_draft(service_request.service_type, data.payload)
    if service_request.service_type == "report":
        normalized["ai_generated_content"] = draft.ai_payload.get("ai_generated_content")
        if "foundation_data" not in normalized:
            normalized["foundation_data"] = draft.ai_payload.get("foundation_data")
    draft.editable_payload = normalized
    draft.content_version += 1
    draft.updated_by = actor.id
    service_request.status = "reviewing"
    service_request.reviewing_at = service_request.reviewing_at or datetime.utcnow()
    service_request.updated_by = actor.id
    await record_audit(
        db,
        actor.id,
        "service_request.draft.save",
        "service_request",
        str(service_request.id),
        target_user_id=service_request.user_id,
        details={"content_version": draft.content_version},
        request=request,
    )
    await db.commit()
    await db.refresh(draft)
    return draft


async def request_more_info(
    db: AsyncSession,
    service_request: ServiceRequest,
    actor: User,
    data: ServiceRequestInfoInput,
    request: Optional[Request] = None,
) -> ServiceRequest:
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if not staff_can_access(service_request, actor):
        raise ValueError("service_request_not_assigned")
    if service_request.status not in {"accepted", "ai_ready", "reviewing", "failed"}:
        raise ValueError("request_info_not_allowed")
    service_request.status = "needs_info"
    service_request.needs_info_reason = data.reason
    service_request.needs_info_at = datetime.utcnow()
    service_request.updated_by = actor.id
    await record_audit(
        db,
        actor.id,
        "service_request.needs_info",
        "service_request",
        str(service_request.id),
        target_user_id=service_request.user_id,
        details={"reason_provided": True},
        request=request,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request
