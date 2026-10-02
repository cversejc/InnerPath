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
from app.application.skill_runtime import queue_case_authoring_skill_run
from app.db.session import get_db
from app.dependencies import get_current_active_user, require_roles
from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
)
from app.domains.content.schemas import (
    ContentFragmentRevisionCreate,
    ContentFragmentRevisionResponse,
    FindingRevisionCreate,
    FindingRevisionResponse,
    EvidenceResponse,
    NarrativeCandidatesCreate,
    NarrativePlanConfirm,
    NarrativePlanResponse,
    NarrativeStateResponse,
    ReportFragmentGenerate,
    ReportCaseContentResponse,
)
from app.domains.content.service import (
    create_content_fragment_revision,
    create_finding_revision,
)
from app.domains.content.findings import current_finding
from app.domains.content.narrative import confirm_narrative_plan, get_current_narrative_plan
from app.domains.service_requests.models import ServiceRequest
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowVersion,
)
from app.domains.skills.models import SkillRun
from app.domains.skills.schemas import SkillRunResponse
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
        "case_evidence_not_found",
        "finding_not_found",
        "fragment_not_found",
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
        "workflow_case_already_delivered",
        "finding_revision_conflict",
        "fragment_revision_conflict",
        "step_not_current",
        "narrative_candidate_run_not_completed",
        "narrative_semantics_changed",
        "narrative_plan_confirmation_required",
        "narrative_step_not_in_review",
        "narrative_skill_unavailable",
    }:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=code)
    if code == "report_case_forbidden":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=code)
    if code in {"narrative_candidate_run_invalid", "narrative_candidate_not_found"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=code)
    if code.startswith(("workflow_", "step_", "narrative_", "report_fragment_", "fragment_narrative_")):
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
    db: AsyncSession,
    case_id: int,
    step_key: str,
    actor: User,
    *,
    require_current_review: bool = False,
) -> tuple[ReportCase, StepTask]:
    report_case = await _case_for_read_or_action(db, case_id, actor, action=True)
    task = await db.scalar(
        select(StepTask)
        .where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == step_key,
        )
        .with_for_update()
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")
    capabilities = {"consultant": {"consultant"}, "admin": {"*"}}
    if (
        task.required_capability
        and "*" not in capabilities.get(actor.role, set())
        and task.required_capability not in capabilities.get(actor.role, set())
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Step capability is required")
    if actor.role == "consultant" and task.assignee_id not in (None, actor.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Step is assigned to another consultant",
        )
    if require_current_review:
        current = await db.scalar(
            select(StepTask)
            .where(
                StepTask.workflow_instance_id == report_case.workflow_instance_id,
                StepTask.status.in_({"READY", "IN_REVIEW", "EXECUTING", "WAITING_REVIEW"}),
            )
            .order_by(StepTask.sequence_no)
            .limit(1)
        )
        if current is None or current.id != task.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="step_not_current")
        if task.status != "IN_REVIEW":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="step_not_in_review")
    return report_case, task


async def _serialize_case_content(
    db: AsyncSession, case_id: int
) -> ReportCaseContentResponse:
    evidence_rows = await db.scalars(
        select(CaseEvidenceItem)
        .where(CaseEvidenceItem.report_case_id == case_id)
        .order_by(CaseEvidenceItem.created_at, CaseEvidenceItem.id)
    )
    finding_rows = await db.scalars(
        select(FindingRevision)
        .where(
            FindingRevision.report_case_id == case_id,
            FindingRevision.is_current.is_(True),
        )
        .order_by(FindingRevision.finding_key)
    )
    fragment_rows = await db.scalars(
        select(ContentFragmentRevision)
        .where(
            ContentFragmentRevision.report_case_id == case_id,
            ContentFragmentRevision.is_current.is_(True),
        )
        .order_by(ContentFragmentRevision.fragment_key)
    )
    return ReportCaseContentResponse(
        evidence=[EvidenceResponse.model_validate(row) for row in evidence_rows],
        findings=[FindingRevisionResponse.model_validate(row) for row in finding_rows],
        fragments=[ContentFragmentRevisionResponse.model_validate(row) for row in fragment_rows],
    )


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


@router.get("/{case_id}/content", response_model=ReportCaseContentResponse)
async def get_report_case_content(
    case_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await _case_for_read_or_action(db, case_id, current_user, action=True)
    return await _serialize_case_content(db, case_id)


@router.get("/{case_id}/narrative", response_model=NarrativeStateResponse)
async def get_report_case_narrative(
    case_id: int,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await _case_for_read_or_action(db, case_id, current_user, action=True)
    current = await get_current_narrative_plan(db, case_id)
    runs = await db.scalars(
        select(SkillRun)
        .where(
            SkillRun.report_case_id == case_id,
            SkillRun.target_type.in_({"NARRATIVE_CANDIDATES", "REPORT_FRAGMENT"}),
        )
        .order_by(SkillRun.created_at.desc(), SkillRun.id.desc())
        .limit(40)
    )
    run_responses = [
        SkillRunResponse.model_validate(row).model_dump(mode="json") for row in runs
    ]
    return NarrativeStateResponse(
        current_plan=(
            NarrativePlanResponse.model_validate(current) if current is not None else None
        ),
        candidate_runs=[row for row in run_responses if row["target_type"] == "NARRATIVE_CANDIDATES"],
        fragment_runs=[row for row in run_responses if row["target_type"] == "REPORT_FRAGMENT"],
    )


@router.post(
    "/{case_id}/steps/{step_key}/narrative-candidates",
    response_model=SkillRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_narrative_candidates(
    case_id: int,
    step_key: str,
    data: NarrativeCandidatesCreate,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_step_action(db, case_id, step_key, current_user, require_current_review=True)
    try:
        run, _created = await queue_case_authoring_skill_run(
            db,
            case_id=case_id,
            step_key=step_key,
            actor=current_user,
            skill_key="report.narrative_plan",
            idempotency_key=data.idempotency_key,
            runtime_instruction=data.runtime_instruction,
        )
        return run
    except ValueError as error:
        await db.rollback()
        if str(error) == "report_case_forbidden":
            raise HTTPException(status_code=403, detail=str(error))
        _workflow_error(error)


@router.post(
    "/{case_id}/narrative-plans/confirm",
    response_model=NarrativePlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_report_case_narrative_plan(
    case_id: int,
    data: NarrativePlanConfirm,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    report_case = await _case_for_read_or_action(db, case_id, current_user, action=True)
    if report_case.workflow_instance_id is None:
        raise HTTPException(status_code=409, detail="workflow_instance_not_found")
    active_step = await db.scalar(
        select(StepTask).where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == "S5",
        )
    )
    if active_step is None:
        raise HTTPException(status_code=404, detail="step_task_not_found")
    await _authorize_step_action(
        db, case_id, "S5", current_user, require_current_review=True
    )
    try:
        plan = await confirm_narrative_plan(
            db,
            report_case_id=case_id,
            skill_run_id=data.skill_run_id,
            candidate_key=data.candidate_key,
            overrides=data.overrides,
            actor_id=current_user.id,
        )
        await db.commit()
        await db.refresh(plan)
        return plan
    except ValueError as error:
        await db.rollback()
        _workflow_error(error)


@router.post(
    "/{case_id}/steps/{step_key}/fragments/generate",
    response_model=SkillRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_report_case_fragment(
    case_id: int,
    step_key: str,
    data: ReportFragmentGenerate,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_step_action(db, case_id, step_key, current_user, require_current_review=True)
    try:
        run, _created = await queue_case_authoring_skill_run(
            db,
            case_id=case_id,
            step_key=step_key,
            actor=current_user,
            skill_key="report.fragment_authoring",
            idempotency_key=data.idempotency_key,
            runtime_instruction=data.runtime_instruction,
            fragment_key=data.fragment_key,
            fragment_title=data.title,
        )
        return run
    except ValueError as error:
        await db.rollback()
        if str(error) == "report_case_forbidden":
            raise HTTPException(status_code=403, detail=str(error))
        _workflow_error(error)


@router.put(
    "/{case_id}/steps/{step_key}/findings/{finding_key}",
    response_model=FindingRevisionResponse,
)
async def revise_report_case_finding(
    case_id: int,
    step_key: str,
    finding_key: str,
    data: FindingRevisionCreate,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    _, task = await _authorize_step_action(
        db, case_id, step_key, current_user, require_current_review=True
    )
    current = await current_finding(db, case_id, finding_key)
    current_revision = current.revision_no if current else None
    if current_revision != data.expected_revision_no:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="finding_revision_conflict",
        )
    values = data.model_dump(exclude={"expected_revision_no"})
    try:
        revision = await create_finding_revision(
            db,
            report_case_id=case_id,
            finding_key=finding_key,
            **values,
            owner_step_task_id=task.id,
            created_by=current_user.id,
        )
        await db.commit()
        await db.refresh(revision)
        return revision
    except ValueError as error:
        await db.rollback()
        _workflow_error(error)


@router.put(
    "/{case_id}/steps/{step_key}/fragments/{fragment_key}",
    response_model=ContentFragmentRevisionResponse,
)
async def revise_report_case_fragment(
    case_id: int,
    step_key: str,
    fragment_key: str,
    data: ContentFragmentRevisionCreate,
    current_user: User = Depends(require_roles("admin", "consultant")),
    db: AsyncSession = Depends(get_db),
):
    _, task = await _authorize_step_action(
        db, case_id, step_key, current_user, require_current_review=True
    )
    current = await db.scalar(
        select(ContentFragmentRevision)
        .where(
            ContentFragmentRevision.report_case_id == case_id,
            ContentFragmentRevision.fragment_key == fragment_key,
            ContentFragmentRevision.is_current.is_(True),
        )
        .with_for_update()
    )
    current_revision = current.revision_no if current else None
    if current_revision != data.expected_revision_no:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="fragment_revision_conflict",
        )
    values = data.model_dump(exclude={"expected_revision_no"})
    values.pop("owner_step_task_id", None)
    try:
        revision = await create_content_fragment_revision(
            db,
            report_case_id=case_id,
            fragment_key=fragment_key,
            **values,
            owner_step_task_id=task.id,
            created_by=current_user.id,
        )
        await db.commit()
        await db.refresh(revision)
        return revision
    except ValueError as error:
        await db.rollback()
        _workflow_error(error)


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
