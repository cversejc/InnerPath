from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.application.workflow_commands import (
    assign_case_step,
    complete_case_step,
    create_workflow_version,
    publish_workflow,
    reopen_case_step,
    return_case_step,
    start_case_step,
)
from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.domains.service_requests.models import ServiceRequest
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowVersion,
)
from app.domains.workflow.schemas import (
    ReportCaseListResponse,
    ReportCaseResponse,
    StepAssignmentInput,
    StepCompleteInput,
    StepReturnInput,
    StepTaskResponse,
    WorkflowInstanceResponse,
    WorkflowVersionCreate,
    WorkflowVersionResponse,
)
from app.models.user import User


router = APIRouter()


def _workflow_error(error: ValueError) -> None:
    code = str(error)
    if code in {
        "report_case_not_found",
        "workflow_instance_not_found",
        "step_task_not_found",
        "workflow_version_not_found",
    }:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=code)
    if code in {
        "step_not_ready",
        "step_not_in_review",
        "workflow_not_active",
        "workflow_step_already_in_review",
        "workflow_next_step_not_pending",
        "workflow_step_order_invalid",
        "step_cannot_reopen",
        "return_target_must_be_previous",
        "workflow_version_immutable",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)
    if code.startswith("workflow_") or code.startswith("step_"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=code
        )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code)


async def _case_for_read_or_action(
    db: AsyncSession, case_id: int, actor: User, *, action: bool = False
) -> ReportCase:
    report_case = await db.get(ReportCase, case_id)
    if report_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report case not found"
        )

    if actor.role == "admin":
        return report_case
    if actor.role == "consultant":
        request_row = None
        if report_case.service_request_id is not None:
            query = select(ServiceRequest).where(
                ServiceRequest.id == report_case.service_request_id
            )
            if action:
                query = query.with_for_update()
            request_row = await db.scalar(query)
        if (
            request_row is None
            or request_row.assigned_consultant_id != actor.id
            or request_row.status in {"withdrawn", "rejected"}
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Report case is not assigned to this consultant",
            )
        return report_case
    if action or report_case.user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report case not found"
        )
    return report_case


async def _authorize_step_action(
    db: AsyncSession, case_id: int, step_key: str, actor: User
) -> ReportCase:
    report_case = await _case_for_read_or_action(db, case_id, actor, action=True)
    if actor.role == "consultant" and report_case.workflow_instance_id is not None:
        task = await db.scalar(
            select(StepTask).where(
                StepTask.workflow_instance_id == report_case.workflow_instance_id,
                StepTask.step_key == step_key,
            )
        )
        if task is not None and task.assignee_id not in (None, actor.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Step is assigned to another consultant",
            )
    return report_case


async def _serialize_case(
    db: AsyncSession, report_case: ReportCase
) -> ReportCaseResponse:
    instance = None
    if report_case.workflow_instance_id is not None:
        workflow = await db.get(WorkflowInstance, report_case.workflow_instance_id)
        if workflow:
            rows = await db.scalars(
                select(StepTask)
                .where(StepTask.workflow_instance_id == workflow.id)
                .order_by(StepTask.sequence_no)
            )
            instance = WorkflowInstanceResponse(
                id=workflow.id,
                workflow_version_id=workflow.workflow_version_id,
                status=workflow.status,
                started_at=workflow.started_at,
                completed_at=workflow.completed_at,
                steps=[StepTaskResponse.model_validate(task) for task in rows],
            )
    return ReportCaseResponse(
        id=report_case.id,
        user_id=report_case.user_id,
        service_request_id=report_case.service_request_id,
        status=report_case.status,
        application_snapshot=report_case.application_snapshot,
        application_submitted_at=report_case.application_submitted_at,
        workflow_instance=instance,
        created_at=report_case.created_at,
        delivered_at=report_case.delivered_at,
        cancelled_at=report_case.cancelled_at,
    )


@router.get("/mine", response_model=ReportCaseListResponse)
async def list_my_report_cases(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.scalars(
        select(ReportCase)
        .where(ReportCase.user_id == current_user.id)
        .order_by(ReportCase.created_at.desc())
    )
    items = [await _serialize_case(db, row) for row in rows]
    return ReportCaseListResponse(total=len(items), items=items)


@router.get("", response_model=ReportCaseListResponse)
async def list_staff_report_cases(
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    query = select(ReportCase).order_by(ReportCase.created_at.desc())
    if current_user.role == "consultant":
        query = query.join(
            ServiceRequest, ServiceRequest.id == ReportCase.service_request_id
        ).where(
            ServiceRequest.assigned_consultant_id == current_user.id,
            ServiceRequest.status.notin_(["withdrawn", "rejected"]),
        )
    rows = await db.scalars(query)
    items = [await _serialize_case(db, row) for row in rows]
    return ReportCaseListResponse(total=len(items), items=items)


@router.post(
    "/workflow-versions", response_model=WorkflowVersionResponse, status_code=201
)
async def create_workflow_version_route(
    data: WorkflowVersionCreate,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        version = await create_workflow_version(
            db,
            current_user.id,
            data.workflow_key,
            data.name,
            data.definition_json,
        )
    except ValueError as error:
        _workflow_error(error)
    return version


@router.get("/workflow-versions", response_model=list[WorkflowVersionResponse])
async def list_workflow_versions(
    workflow_key: Optional[str] = None,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    query = select(WorkflowVersion).order_by(
        WorkflowVersion.workflow_key, WorkflowVersion.version.desc()
    )
    if workflow_key:
        query = query.where(WorkflowVersion.workflow_key == workflow_key)
    return list((await db.scalars(query)).all())


@router.get("/{case_id}", response_model=ReportCaseResponse)
async def get_report_case(
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    report_case = await _case_for_read_or_action(db, case_id, current_user)
    return await _serialize_case(db, report_case)


@router.post(
    "/workflow-versions/{version_id}/publish", response_model=WorkflowVersionResponse
)
async def publish_workflow_version_route(
    version_id: int,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await publish_workflow(db, current_user.id, version_id)
    except ValueError as error:
        _workflow_error(error)


@router.post("/{case_id}/steps/{step_key}/start", response_model=StepTaskResponse)
async def start_report_case_step(
    case_id: int,
    step_key: str,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_step_action(db, case_id, step_key, current_user)
    try:
        task = await start_case_step(
            db,
            current_user.id,
            case_id,
            step_key,
            audit_context_from_request(request),
        )
    except ValueError as error:
        _workflow_error(error)
    return task


@router.post("/{case_id}/steps/{step_key}/complete", response_model=StepTaskResponse)
async def complete_report_case_step(
    case_id: int,
    step_key: str,
    data: StepCompleteInput,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_step_action(db, case_id, step_key, current_user)
    try:
        task = await complete_case_step(
            db,
            current_user.id,
            case_id,
            step_key,
            data.result_json,
            audit_context_from_request(request),
        )
    except ValueError as error:
        _workflow_error(error)
    return task


@router.post("/{case_id}/steps/{step_key}/return", response_model=StepTaskResponse)
async def return_report_case_step(
    case_id: int,
    step_key: str,
    data: StepReturnInput,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_step_action(db, case_id, step_key, current_user)
    try:
        task = await return_case_step(
            db,
            current_user.id,
            case_id,
            step_key,
            data.target_step_key,
            data.reason,
            audit_context_from_request(request),
        )
    except ValueError as error:
        _workflow_error(error)
    return task


@router.post("/{case_id}/steps/{step_key}/reopen", response_model=StepTaskResponse)
async def reopen_report_case_step(
    case_id: int,
    step_key: str,
    request: Request,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_step_action(db, case_id, step_key, current_user)
    try:
        task = await reopen_case_step(
            db,
            current_user.id,
            case_id,
            step_key,
            audit_context_from_request(request),
        )
    except ValueError as error:
        _workflow_error(error)
    return task


@router.patch("/{case_id}/steps/{step_key}/assignment", response_model=StepTaskResponse)
async def assign_report_case_step(
    case_id: int,
    step_key: str,
    data: StepAssignmentInput,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    await _case_for_read_or_action(db, case_id, current_user, action=True)
    if data.assignee_id is not None:
        assignee = await db.get(User, data.assignee_id)
        if not assignee or assignee.role != "consultant" or not assignee.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Consultant not found"
            )
    try:
        return await assign_case_step(
            db,
            current_user.id,
            case_id,
            step_key,
            data.assignee_id,
            audit_context_from_request(request),
        )
    except ValueError as error:
        _workflow_error(error)
