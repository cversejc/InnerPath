from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.service_requests.models import ServiceRequest
from app.models.user import User
from app.domains.service_requests.schemas import (
    ServiceRequestDraftResponse,
    ServiceRequestResponse,
    ServiceRequestTaskResponse,
    ServiceRequestWorkspaceResponse,
)
from app.services.service_request_service import serialize_service_request, serialize_task


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
