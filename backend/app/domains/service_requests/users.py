"""User-facing service request lifecycle."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ServiceRequest
from app.models.user import User
from .schemas import ServiceRequestCreate, ServiceRequestUpdate
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from .payloads import _normalize_payload, payload_from_create, payload_from_update
from .repository import _append_revision, _get_draft, _get_request_for_update


async def create_service_request(
    db: AsyncSession,
    user: User,
    data: ServiceRequestCreate,
    audit_context: Optional[AuditContext] = None,
    *,
    commit: bool = True,
) -> ServiceRequest:
    if data.service_type == "calendar":
        raise ValueError("calendar_service_request_retired")
    payload, idempotency_key = payload_from_create(data, user)
    if idempotency_key:
        existing = await db.scalar(
            select(ServiceRequest).where(
                ServiceRequest.user_id == user.id,
                ServiceRequest.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return existing

    service_request = ServiceRequest(
        user_id=user.id,
        service_type=data.service_type,
        status="submitted",
        request_payload=payload,
        idempotency_key=idempotency_key,
    )
    db.add(service_request)
    try:
        await db.flush()
        await record_audit(
            db,
            user.id,
            "service_request.create",
            "service_request",
            str(service_request.id),
            target_user_id=user.id,
            details={"service_type": data.service_type},
            audit_context=audit_context,
        )
        if commit:
            await db.commit()
    except IntegrityError:
        # A double submit can race the lookup above.  The unique constraint is
        # the final idempotency guard; return the request created by the other
        # transaction when it wins the race.
        await db.rollback()
        if idempotency_key:
            existing = await db.scalar(
                select(ServiceRequest).where(
                    ServiceRequest.user_id == user.id,
                    ServiceRequest.idempotency_key == idempotency_key,
                )
            )
            if existing:
                return existing
        raise
    await db.refresh(service_request)
    return service_request

async def get_user_service_requests(
    db: AsyncSession,
    user_id: int,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
) -> list[ServiceRequest]:
    query = select(ServiceRequest).where(ServiceRequest.user_id == user_id)
    if status:
        query = query.where(ServiceRequest.status == status)
    if service_type:
        query = query.where(ServiceRequest.service_type == service_type)
    result = await db.execute(query.order_by(ServiceRequest.created_at.desc()))
    return list(result.scalars().all())

async def get_service_request(db: AsyncSession, request_id: int) -> Optional[ServiceRequest]:
    return await db.get(ServiceRequest, request_id)

async def update_user_service_request(
    db: AsyncSession,
    service_request: ServiceRequest,
    user: User,
    data: ServiceRequestUpdate,
    audit_context: Optional[AuditContext] = None,
) -> ServiceRequest:
    if service_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None or locked_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if service_request.status not in {"submitted", "needs_info"}:
        raise ValueError("service_request_locked")
    service_request.request_payload = payload_from_update(service_request, data, user)
    service_request.updated_by = user.id
    await record_audit(
        db,
        user.id,
        "service_request.update",
        "service_request",
        str(service_request.id),
        target_user_id=user.id,
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request

async def resubmit_service_request(
    db: AsyncSession,
    service_request: ServiceRequest,
    user: User,
    audit_context: Optional[AuditContext] = None,
) -> ServiceRequest:
    if service_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None or locked_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if service_request.status != "needs_info":
        raise ValueError("service_request_not_waiting_for_info")
    submitted_profile_version = (service_request.request_payload or {}).get("profile_version")
    if submitted_profile_version is not None and int(submitted_profile_version) != int(user.profile_version or 1):
        raise ValueError("profile_version_conflict")
    _normalize_payload(
        service_request.service_type,
        (service_request.request_payload or {}).get("profile") or {},
        (service_request.request_payload or {}).get("selected_topics", []),
        (service_request.request_payload or {}).get("additional_info"),
        (service_request.request_payload or {}).get("calendar_goal"),
        (service_request.request_payload or {}).get("start_date"),
        (service_request.request_payload or {}).get("context"),
        (service_request.request_payload or {}).get("profile_version"),
    )
    old_draft = await _get_draft(db, service_request.id)
    if old_draft:
        await _append_revision(db, service_request.id, "before_resubmit", old_draft.editable_payload, user.id)
        await db.delete(old_draft)
    service_request.status = "accepted" if service_request.assigned_consultant_id else "submitted"
    if service_request.assigned_consultant_id:
        service_request.accepted_at = datetime.utcnow()
    service_request.needs_info_reason = None
    service_request.last_error = None
    service_request.updated_by = user.id
    await record_audit(
        db,
        user.id,
        "service_request.resubmit",
        "service_request",
        str(service_request.id),
        target_user_id=user.id,
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request

async def withdraw_service_request(
    db: AsyncSession,
    service_request: ServiceRequest,
    user: User,
    audit_context: Optional[AuditContext] = None,
) -> ServiceRequest:
    if service_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    locked_request = await _get_request_for_update(db, service_request.id)
    if locked_request is None or locked_request.user_id != user.id:
        raise ValueError("service_request_not_found")
    service_request = locked_request
    if service_request.status not in {"submitted", "needs_info"}:
        raise ValueError("service_request_cannot_withdraw")
    service_request.status = "withdrawn"
    service_request.withdrawn_at = datetime.utcnow()
    service_request.updated_by = user.id
    await record_audit(
        db,
        user.id,
        "service_request.withdraw",
        "service_request",
        str(service_request.id),
        target_user_id=user.id,
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(service_request)
    return service_request
