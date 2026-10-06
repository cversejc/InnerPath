from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.service_requests.models import ServiceRequest
from app.models.user import User
from app.domains.service_requests.schemas import (
    ServiceRequestAssignmentUpdate,
    ServiceRequestInfoInput,
    ServiceRequestResponse,
    AdminServiceRequestListItem,
    AdminServiceRequestListResponse,
)
from app.domains.audit.service import record_audit
from app.domains.service_requests.service import (
    consultant_can_cover_specialty,
    get_service_request,
    list_admin_service_requests,
)
from app.api.v1.service_request_api_support import _serialize_public

admin_router = APIRouter()
@admin_router.get("", response_model=AdminServiceRequestListResponse)
async def list_admin_requests(
    request_status: Optional[str] = Query(None, alias="status", max_length=30),
    service_type: Optional[str] = Query("report", pattern="^(report|calendar)$"),
    user_id: Optional[int] = Query(None, ge=1),
    consultant_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=100),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    rows, total = await list_admin_service_requests(
        db,
        status=request_status,
        service_type=service_type,
        user_id=user_id,
        consultant_id=consultant_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )
    items = [
        AdminServiceRequestListItem(
            id=item.id,
            user_id=item.user_id,
            user_name=target_user.name,
            user_phone=target_user.phone,
            service_type=item.service_type,
            consultation_type=item.consultation_type,
            status=item.status,
            request_payload=item.request_payload or {},
            assigned_consultant_id=item.assigned_consultant_id,
            assigned_consultant_name=consultant.name if consultant else None,
            result_type=item.result_type,
            result_id=item.result_id,
            needs_info_reason=item.needs_info_reason,
            rejection_reason=item.rejection_reason,
            last_error=item.last_error,
            created_at=item.created_at,
            updated_at=item.updated_at,
            accepted_at=item.accepted_at,
            ai_started_at=item.ai_started_at,
            ai_completed_at=item.ai_completed_at,
            reviewing_at=item.reviewing_at,
            needs_info_at=item.needs_info_at,
            failed_at=item.failed_at,
            delivered_at=item.delivered_at,
            withdrawn_at=item.withdrawn_at,
            rejected_at=item.rejected_at,
        )
        for item, target_user, consultant in rows
    ]
    return AdminServiceRequestListResponse(total=total, page=page, size=size, items=items)


@admin_router.patch("/{request_id}/assignment", response_model=ServiceRequestResponse)
async def update_request_assignment(
    request_id: int,
    data: ServiceRequestAssignmentUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    locked_result = await db.execute(
        select(ServiceRequest).where(ServiceRequest.id == request_id).with_for_update()
    )
    service_request = locked_result.scalar_one_or_none()
    if not service_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    if service_request.status in {"delivered", "withdrawn", "rejected"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is closed")
    consultant = None
    if data.consultant_id is not None:
        consultant = await db.get(User, data.consultant_id)
        if not consultant or consultant.role != "consultant" or not consultant.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consultant not found")
    consultation_type = data.consultation_type or service_request.consultation_type
    if consultant and service_request.service_type == "report":
        if consultation_type is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Select a consultation direction first")
        if not consultant_can_cover_specialty(consultant, consultation_type):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consultant does not cover this consultation direction")
    service_request.assigned_consultant_id = data.consultant_id
    if data.consultation_type is not None:
        service_request.consultation_type = data.consultation_type
    if consultant and service_request.status == "submitted":
        service_request.status = "accepted"
        service_request.accepted_at = datetime.utcnow()
    elif consultant is None and service_request.status == "accepted":
        service_request.status = "submitted"
    service_request.updated_by = current_user.id
    await record_audit(
        db,
        current_user.id,
        "service_request.assignment.update",
        "service_request",
        str(request_id),
        target_user_id=service_request.user_id,
        details={"consultant_id": data.consultant_id, "consultation_type": service_request.consultation_type},
        audit_context=audit_context_from_request(request),
    )
    await db.commit()
    await db.refresh(service_request)
    return await _serialize_public(db, service_request)


@admin_router.post("/{request_id}/reject", response_model=ServiceRequestResponse)
async def reject_request(
    request_id: int,
    data: ServiceRequestInfoInput,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    if service_request.status not in {"submitted", "accepted", "needs_info", "failed"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request cannot be rejected")
    service_request.status = "rejected"
    service_request.rejection_reason = data.reason
    service_request.rejected_at = datetime.utcnow()
    service_request.updated_by = current_user.id
    await record_audit(
        db,
        current_user.id,
        "service_request.reject",
        "service_request",
        str(request_id),
        target_user_id=service_request.user_id,
        audit_context=audit_context_from_request(request),
    )
    await db.commit()
    await db.refresh(service_request)
    return await _serialize_public(db, service_request)
