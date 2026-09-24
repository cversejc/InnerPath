from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.models.service_request import ServiceRequest
from app.models.user import User
from app.schemas.service_request import (
    ServiceRequestAssignmentUpdate,
    ServiceRequestCreate,
    ServiceRequestDraftResponse,
    ServiceRequestDraftUpdate,
    ServiceRequestInfoInput,
    ServiceRequestListResponse,
    ServiceRequestRegenerateInput,
    ServiceRequestResponse,
    ServiceRequestTaskResponse,
    ServiceRequestUpdate,
    ServiceRequestWorkspaceResponse,
    StaffServiceRequestListItem,
    StaffServiceRequestListResponse,
)
from app.services.service_request_service import (
    accept_service_request,
    create_service_request,
    deliver_service_request,
    enqueue_ai_draft,
    get_service_request,
    get_workspace,
    list_staff_service_requests,
    get_user_service_requests,
    request_more_info,
    save_service_request_draft,
    serialize_service_request,
    serialize_task,
    staff_can_access,
    update_user_service_request,
    withdraw_service_request,
    resubmit_service_request,
)
from app.services.audit_service import record_audit


router = APIRouter()
staff_router = APIRouter()
task_router = APIRouter()
admin_router = APIRouter()


def _detail_for_error(error: ValueError) -> tuple[int, str]:
    code = str(error)
    if code in {"service_request_not_found", "service_request_draft_not_found"}:
        return status.HTTP_404_NOT_FOUND, "Service request not found"
    if code in {"service_request_not_assigned"}:
        return status.HTTP_403_FORBIDDEN, "Service request is not assigned to this consultant"
    if code in {"draft_version_conflict"}:
        return status.HTTP_409_CONFLICT, "Draft has changed; refresh before saving"
    if code in {"service_request_locked", "service_request_already_taken"}:
        return status.HTTP_409_CONFLICT, code
    if code in {"service_request_cannot_withdraw", "service_request_not_waiting_for_info"}:
        return status.HTTP_409_CONFLICT, code
    return status.HTTP_400_BAD_REQUEST, code


def _raise_value_error(error: ValueError) -> None:
    code, message = _detail_for_error(error)
    raise HTTPException(status_code=code, detail=message)


async def _serialize_public(db: AsyncSession, service_request: ServiceRequest) -> ServiceRequestResponse:
    consultant_name = None
    if service_request.assigned_consultant_id:
        consultant_name = await db.scalar(
            select(User.name).where(User.id == service_request.assigned_consultant_id)
        )
    return ServiceRequestResponse.model_validate(
        serialize_service_request(service_request, consultant_name=consultant_name)
    )


def _workspace_response(workspace: dict) -> ServiceRequestWorkspaceResponse:
    draft = workspace.get("draft")
    task = workspace.get("task")
    draft_response = None
    if draft:
        draft_response = ServiceRequestDraftResponse(
            request_id=draft.request_id,
            ai_payload=draft.ai_payload,
            editable_payload=draft.editable_payload,
            ai_version=draft.ai_version,
            content_version=draft.content_version,
            updated_at=draft.updated_at,
        )
    task_response = ServiceRequestTaskResponse.model_validate(serialize_task(task)) if task else None
    return ServiceRequestWorkspaceResponse(
        request=ServiceRequestResponse.model_validate(workspace["request"]),
        user=workspace["user"],
        draft=draft_response,
        task=task_response,
    )


@router.post("", response_model=ServiceRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    data: ServiceRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service_request = await create_service_request(db, current_user, data, request=request)
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


@router.get("", response_model=ServiceRequestListResponse)
async def list_my_requests(
    request_status: Optional[str] = Query(None, alias="status", max_length=30),
    service_type: Optional[str] = Query(None, pattern="^(report|calendar)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    items = await get_user_service_requests(db, current_user.id, request_status, service_type)
    return ServiceRequestListResponse(items=[await _serialize_public(db, item) for item in items], total=len(items))


@router.get("/{request_id}", response_model=ServiceRequestResponse)
async def get_my_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request or service_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    return await _serialize_public(db, service_request)


@router.patch("/{request_id}", response_model=ServiceRequestResponse)
async def update_my_request(
    request_id: int,
    data: ServiceRequestUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request or service_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        service_request = await update_user_service_request(db, service_request, current_user, data, request=request)
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


@router.post("/{request_id}/resubmit", response_model=ServiceRequestResponse)
async def resubmit_my_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request or service_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        service_request = await resubmit_service_request(db, service_request, current_user, request=request)
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


@router.post("/{request_id}/withdraw", response_model=ServiceRequestResponse)
async def withdraw_my_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request or service_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        service_request = await withdraw_service_request(db, service_request, current_user, request=request)
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


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
        service_request = await accept_service_request(db, request_id, current_user, request=request)
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
    return _workspace_response(await get_workspace(db, service_request))


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
        task = await enqueue_ai_draft(db, service_request, current_user, request=request)
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
        draft = await save_service_request_draft(db, service_request, current_user, data, request=request)
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
        service_request = await request_more_info(db, service_request, current_user, data, request=request)
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
        task = await enqueue_ai_draft(
            db,
            service_request,
            current_user,
            request=request,
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
        service_request = await deliver_service_request(db, service_request, current_user, request=request)
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


@task_router.get("/{task_id}", response_model=ServiceRequestTaskResponse)
async def get_staff_task(
    task_id: str,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    from app.models.service_request import ServiceRequestTask

    task = await db.get(ServiceRequestTask, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    service_request = await get_service_request(db, task.request_id)
    if not service_request or not staff_can_access(service_request, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task is not assigned")
    return ServiceRequestTaskResponse.model_validate(serialize_task(task))


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
