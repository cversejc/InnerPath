from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.service_requests.models import ServiceRequest
from app.models.user import User
from app.domains.service_requests.schemas import (
    ServiceRequestAssignmentUpdate,
    ServiceRequestInfoInput,
    ServiceRequestResponse,
    StaffServiceRequestListItem,
    StaffServiceRequestListResponse,
)
from app.domains.audit.service import record_audit
from app.domains.service_requests.service import get_service_request, list_staff_service_requests
from app.api.v1.service_request_api_support import _serialize_public

admin_router = APIRouter()
@admin_router.get("", response_model=StaffServiceRequestListResponse)
async def list_admin_requests(
    request_status: Optional[str] = Query(None, alias="status", max_length=30),
    service_type: Optional[str] = Query(None, pattern="^(report|calendar)$"),
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_staff_service_requests(db, current_user, request_status, service_type, "all")
    items = []
    for item, target_user in rows:
        assigned_name = None
        if item.assigned_consultant_id:
            assigned_name = await db.scalar(select(User.name).where(User.id == item.assigned_consultant_id))
        items.append(
            StaffServiceRequestListItem(
                id=item.id,
                user_id=item.user_id,
                user_name=target_user.name if target_user else None,
                service_type=item.service_type,
                status=item.status,
                request_preview=item.request_payload or {},
                assigned_consultant_id=item.assigned_consultant_id,
                assigned_consultant_name=assigned_name,
                needs_info_reason=item.needs_info_reason,
                last_error=item.last_error,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return StaffServiceRequestListResponse(total=len(items), items=items)


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
    service_request.assigned_consultant_id = data.consultant_id
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
        details={"consultant_id": data.consultant_id},
        request=request,
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
        request=request,
    )
    await db.commit()
    await db.refresh(service_request)
    return await _serialize_public(db, service_request)
