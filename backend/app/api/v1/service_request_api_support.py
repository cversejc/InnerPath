from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.service_requests.models import ServiceRequest
from app.domains.workflow.models import ReportCase, StepTask
from app.models.user import User
from app.domains.service_requests.schemas import (
    ServiceRequestDraftResponse,
    ServiceRequestResponse,
    ServiceRequestTaskResponse,
    ServiceRequestWorkspaceResponse,
)
from app.domains.service_requests.service import serialize_service_request, serialize_task


def project_report_case_status(case_status: str, step_status: str | None, fallback: str) -> str:
    if fallback in {"withdrawn", "rejected"}:
        return fallback
    if case_status == "READY_TO_DELIVER":
        return "workflow_complete"
    if case_status == "DELIVERED":
        return "delivered"
    if case_status == "BLOCKED":
        return "needs_info"
    if case_status == "CANCELLED":
        return fallback if fallback in {"withdrawn", "rejected"} else "rejected"
    if fallback == "submitted":
        return "submitted"
    if step_status == "IN_REVIEW":
        return "reviewing"
    return "accepted"


async def report_case_progress_for_requests(
    db: AsyncSession, request_ids: list[int]
) -> dict[int, dict[str, int | str | None]]:
    if not request_ids:
        return {}
    cases = list(
        await db.scalars(
            select(ReportCase).where(ReportCase.service_request_id.in_(request_ids))
        )
    )
    workflow_ids = [case.workflow_instance_id for case in cases if case.workflow_instance_id]
    active_steps = []
    if workflow_ids:
        active_steps = list(
            await db.scalars(
                select(StepTask)
                .where(
                    StepTask.workflow_instance_id.in_(workflow_ids),
                    StepTask.status.in_(
                        ["READY", "IN_REVIEW", "EXECUTING", "WAITING_REVIEW"]
                    ),
                )
                .order_by(StepTask.sequence_no)
            )
        )
    current_by_workflow = {}
    for step in active_steps:
        current_by_workflow.setdefault(step.workflow_instance_id, step)
    return {
        case.service_request_id: {
            "report_case_id": case.id,
            "report_case_status": case.status,
            "current_step_key": (
                current_by_workflow[case.workflow_instance_id].step_key
                if case.workflow_instance_id in current_by_workflow
                else None
            ),
            "current_step_status": (
                current_by_workflow[case.workflow_instance_id].status
                if case.workflow_instance_id in current_by_workflow
                else None
            ),
        }
        for case in cases
        if case.service_request_id is not None
    }


def _detail_for_error(error: ValueError) -> tuple[int, str]:
    code = str(error)
    if code in {"service_request_not_found", "service_request_draft_not_found"}:
        return status.HTTP_404_NOT_FOUND, "Service request not found"
    if code in {"service_request_not_assigned"}:
        return status.HTTP_403_FORBIDDEN, "Service request is not assigned to this consultant"
    if code in {"draft_version_conflict"}:
        return status.HTTP_409_CONFLICT, "Draft has changed; refresh before saving"
    if code == "profile_version_conflict":
        return status.HTTP_409_CONFLICT, "Profile has changed; refresh before submitting"
    if code in {"service_request_locked", "service_request_already_taken"}:
        return status.HTTP_409_CONFLICT, code
    if code == "report_case_workflow_required":
        return status.HTTP_409_CONFLICT, "该报告申请已进入 Case 工作流，请在报告工作区继续处理。"
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
    payload = serialize_service_request(service_request, consultant_name=consultant_name)
    if service_request.service_type == "report":
        report_case = await db.scalar(
            select(ReportCase).where(ReportCase.service_request_id == service_request.id)
        )
        if report_case:
            payload["report_case_id"] = report_case.id
            payload["report_case_status"] = report_case.status
            current_step = None
            if report_case.workflow_instance_id:
                current_step = await db.scalar(
                    select(StepTask)
                    .where(
                        StepTask.workflow_instance_id == report_case.workflow_instance_id,
                        StepTask.status.in_(["READY", "IN_REVIEW", "EXECUTING", "WAITING_REVIEW"]),
                    )
                    .order_by(StepTask.sequence_no)
                    .limit(1)
                )
                payload["current_step_key"] = current_step.step_key if current_step else None
            payload["status"] = project_report_case_status(
                report_case.status,
                current_step.status if current_step else None,
                service_request.status,
            )
    return ServiceRequestResponse.model_validate(payload)


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
