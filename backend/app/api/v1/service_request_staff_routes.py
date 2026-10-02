from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.domains.service_requests.schemas import (
    ServiceRequestDraftResponse,
    ServiceRequestDraftUpdate,
    ServiceRequestInfoInput,
    ServiceRequestRegenerateInput,
    ServiceRequestResponse,
    ServiceRequestTaskResponse,
    ServiceRequestWorkspaceResponse,
    StaffServiceRequestListItem,
    StaffServiceRequestListResponse,
)
from app.application.service_request_delivery import deliver_service_request
from app.application.service_request_ai import start_service_request_ai_draft
from app.application.report_cases import ensure_legacy_report_request
from app.domains.service_requests.service import (
    accept_service_request,
    get_service_request,
    get_workspace,
    list_staff_service_requests,
    request_more_info,
    save_service_request_draft,
    serialize_task,
)
from app.api.v1.service_request_api_support import _raise_value_error, _serialize_public, _workspace_response
from app.tasks.service_request_dispatch import dispatch_service_request_draft

staff_router = APIRouter()
@staff_router.get("", response_model=StaffServiceRequestListResponse)
async def list_staff_requests(
    scope: str = Query("mine", pattern="^(available|mine|all)$"),
    request_status: Optional[str] = Query(None, alias="status", max_length=30),
    service_type: Optional[str] = Query(None, pattern="^(report|calendar)$"),
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role == "consultant" and scope == "all":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Consultants cannot list all requests")
    rows = await list_staff_service_requests(db, current_user, request_status, service_type, scope)
    items = []
    for item, target_user in rows:
        assigned_name = None
        if item.assigned_consultant_id:
            assigned_name = await db.scalar(select(User.name).where(User.id == item.assigned_consultant_id))
        payload = item.request_payload or {}
        profile = payload.get("profile") or {}
        items.append(
            StaffServiceRequestListItem(
                id=item.id,
                user_id=item.user_id,
                user_name=target_user.name if target_user else None,
                service_type=item.service_type,
                status=item.status,
                request_preview={
                    "selected_topics": payload.get("selected_topics", []),
                    "calendar_goal": payload.get("calendar_goal"),
                    "start_date": payload.get("start_date"),
                    "additional_info": payload.get("additional_info") if scope != "available" or current_user.role == "admin" else None,
                    "birth_year": profile.get("birth_year") if scope != "available" or current_user.role == "admin" else None,
                },
                assigned_consultant_id=item.assigned_consultant_id,
                assigned_consultant_name=assigned_name,
                needs_info_reason=item.needs_info_reason,
                last_error=item.last_error,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )
    return StaffServiceRequestListResponse(total=len(items), items=items)


@staff_router.post("/{request_id}/accept", response_model=ServiceRequestResponse)
async def accept_staff_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    try:
        service_request = await accept_service_request(
            db,
            request_id,
            current_user,
            audit_context=audit_context_from_request(request),
        )
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


@staff_router.get("/{request_id}", response_model=ServiceRequestWorkspaceResponse)
async def get_staff_request_workspace(
    request_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    if not staff_can_access(service_request, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Service request is not assigned")
    workspace = await get_workspace(db, service_request)
    if service_request.service_type == "report":
        workspace["request"] = (await _serialize_public(db, service_request)).model_dump()
    return _workspace_response(workspace)


@staff_router.post("/{request_id}/ai-draft", response_model=ServiceRequestTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_ai_draft(
    request_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        await ensure_legacy_report_request(db, service_request)
        task = await start_service_request_ai_draft(
            db,
            service_request,
            current_user,
            audit_context=audit_context_from_request(request),
            dispatch_task=dispatch_service_request_draft,
        )
    except ValueError as error:
        _raise_value_error(error)
    return ServiceRequestTaskResponse.model_validate(serialize_task(task))


@staff_router.put("/{request_id}/draft", response_model=ServiceRequestDraftResponse)
async def save_staff_draft(
    request_id: int,
    data: ServiceRequestDraftUpdate,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        await ensure_legacy_report_request(db, service_request)
        draft = await save_service_request_draft(
            db,
            service_request,
            current_user,
            data,
            audit_context=audit_context_from_request(request),
        )
    except ValueError as error:
        _raise_value_error(error)
    return ServiceRequestDraftResponse(
        request_id=draft.request_id,
        ai_payload=draft.ai_payload,
        editable_payload=draft.editable_payload,
        ai_version=draft.ai_version,
        content_version=draft.content_version,
        updated_at=draft.updated_at,
    )


@staff_router.post("/{request_id}/request-info", response_model=ServiceRequestResponse)
async def request_staff_info(
    request_id: int,
    data: ServiceRequestInfoInput,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        await ensure_legacy_report_request(db, service_request)
        service_request = await request_more_info(
            db,
            service_request,
            current_user,
            data,
            audit_context=audit_context_from_request(request),
        )
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


@staff_router.post("/{request_id}/retry-ai", response_model=ServiceRequestTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def retry_staff_ai(
    request_id: int,
    data: ServiceRequestRegenerateInput,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        await ensure_legacy_report_request(db, service_request)
        task = await start_service_request_ai_draft(
            db,
            service_request,
            current_user,
            audit_context=audit_context_from_request(request),
            dispatch_task=dispatch_service_request_draft,
            force=data.confirm_overwrite,
            retry_of_task_id=None,
        )
    except ValueError as error:
        _raise_value_error(error)
    return ServiceRequestTaskResponse.model_validate(serialize_task(task))


@staff_router.post("/{request_id}/deliver", response_model=ServiceRequestResponse)
async def deliver_staff_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        service_request = await deliver_service_request(
            db,
            service_request,
            current_user,
            audit_context=audit_context_from_request(request),
        )
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)
