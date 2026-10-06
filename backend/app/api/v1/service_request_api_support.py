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
from app.domains.service_requests.service import serialize_service_request, serialize_task
from app.domains.calendar.requests import serialize_calendar_request
from app.domains.service_requests.schemas import ServiceRequestResponse as PublicServiceRequestResponse


def _detail_for_error(error: ValueError) -> tuple[int, str]:
    code = str(error)
    if code == "profile_version_conflict":
        return status.HTTP_409_CONFLICT, "个人档案已更新，请刷新后确认最新资料再提交。"
    if code == "calendar_service_request_retired":
        return status.HTTP_410_GONE, "日历需在报告交付后生成，请先完成报告申请。"
    if code == "report_request_requires_focus_topics":
        return status.HTTP_422_UNPROCESSABLE_ENTITY, "至少选择一个报告关注议题。"
    if code == "report_request_requires_current_challenge":
        return status.HTTP_422_UNPROCESSABLE_ENTITY, "请填写这次希望咨询师关注的问题。"
    if code == "report_request_requires_expected_outcomes":
        return status.HTTP_422_UNPROCESSABLE_ENTITY, "至少选择一个期望获得的结果。"
    if code == "calendar_request_must_cover_30_days":
        return status.HTTP_422_UNPROCESSABLE_ENTITY, "日历周期需覆盖 30 天，请重新选择日期。"
    if code in {"service_request_not_found", "service_request_draft_not_found"}:
        return status.HTTP_404_NOT_FOUND, "Service request not found"
    if code in {"service_request_not_assigned"}:
        return status.HTTP_403_FORBIDDEN, "Service request is not assigned to this consultant"
    if code == "consultant_specialty_mismatch":
        return status.HTTP_403_FORBIDDEN, "当前咨询师不具备该申请方向的能力。"
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
    serialized = serialize_service_request(service_request, consultant_name=consultant_name)
    if service_request.service_type == "calendar":
        serialized["workflow_type"] = "calendar_legacy"
    return ServiceRequestResponse.model_validate(serialized)


async def _serialize_calendar_generation(db: AsyncSession, calendar_request) -> PublicServiceRequestResponse:
    payload = await serialize_calendar_request(db, calendar_request)
    is_current_flow = payload["status"] in {"processing", "delivered", "failed"} and bool(payload["task_id"])
    is_delivered = payload["status"] in {"delivered", "fulfilled"} and payload["calendar_id"] is not None
    return PublicServiceRequestResponse.model_validate(
        {
            "id": payload["id"],
            "service_type": "calendar",
            "workflow_type": "calendar_generation" if is_current_flow else "calendar_legacy",
            "status": "ai_processing" if payload["status"] == "processing" else "delivered" if is_delivered else payload["status"],
            "request_payload": {
                "source_report_id": payload["source_report_id"],
                "start_date": payload["start_date"],
                "end_date": payload["end_date"],
                "focus_topics": payload["focus_topics"],
                "selected_topics": payload["focus_topics"],
                "usage_scenario": payload["usage_scenario"],
                "calendar_goal": payload["goal"],
                "additional_info": payload["additional_info"],
                "expected_outcomes": payload["expected_outcomes"],
            },
            "result_type": "calendar" if is_delivered else None,
            "result_id": payload["calendar_id"] if is_delivered else None,
            "last_error": payload["generation_error"],
            "progress": payload["progress"],
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
        }
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
