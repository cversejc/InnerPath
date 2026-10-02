from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.service_requests.models import ServiceRequest
from app.domains.skills.definitions import (
    DEFAULT_SKILL_KEY,
    default_skill_specification,
)
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.runtime import (
    DeepSeekGateway,
    ModelGateway,
    SkillExecutionError,
    execute_skill,
)
from app.domains.skills.service import create_skill_run, ensure_default_skill_version
from app.domains.workflow.definitions import (
    DEFAULT_WORKFLOW_KEY,
    default_workflow_definition,
)
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowOutbox,
    WorkflowVersion,
)
from app.domains.workflow.service import create_workflow_draft, publish_workflow_version
from app.models.user import User


async def ensure_skill_workflow_version(db: AsyncSession) -> WorkflowVersion:
    existing = await db.scalar(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_key == DEFAULT_WORKFLOW_KEY,
            WorkflowVersion.version == 2,
        )
    )
    if existing and existing.status == "PUBLISHED":
        return existing
    if existing:
        raise ValueError("skill_workflow_version_not_published")
    skill = await ensure_default_skill_version(db)
    definition = default_workflow_definition()
    authoring_step = next(
        step for step in definition["steps"] if step["step_key"] == "S5"
    )
    authoring_step["executor"] = "HYBRID"
    authoring_step["config"].update(
        {"skill_key": DEFAULT_SKILL_KEY, "skill_version_id": skill.id}
    )
    try:
        async with db.begin_nested():
            version = await create_workflow_draft(
                db,
                DEFAULT_WORKFLOW_KEY,
                "咨询师报告生产流程",
                definition,
                created_by=None,
            )
            await publish_workflow_version(db, version.id, published_by=None)
        return version
    except IntegrityError:
        existing = await db.scalar(
            select(WorkflowVersion).where(
                WorkflowVersion.workflow_key == DEFAULT_WORKFLOW_KEY,
                WorkflowVersion.version == 2,
            )
        )
        if existing and existing.status == "PUBLISHED":
            return existing
        raise


def _safe_input_snapshot(input_data: dict[str, Any]) -> dict[str, Any]:
    spec = default_skill_specification()
    from app.domains.skills.runtime import build_context_envelope

    envelope = build_context_envelope(input_data, spec)
    return envelope


async def _authorize_case(db: AsyncSession, case_id: int, actor: User) -> ReportCase:
    report_case = await db.get(ReportCase, case_id)
    if report_case is None:
        raise ValueError("report_case_not_found")
    if actor.role == "admin":
        return report_case
    if actor.role != "consultant" or report_case.service_request_id is None:
        raise ValueError("report_case_forbidden")
    request_row = await db.scalar(
        select(ServiceRequest).where(
            ServiceRequest.id == report_case.service_request_id
        )
    )
    if (
        request_row is None
        or request_row.assigned_consultant_id != actor.id
        or request_row.status in {"withdrawn", "rejected"}
    ):
        raise ValueError("report_case_forbidden")
    return report_case


async def _queue_run(
    db: AsyncSession,
    *,
    version_id: int,
    idempotency_key: str,
    input_data: dict[str, Any],
    runtime_instruction: str | None,
    target_type: str,
    target_key: str | None,
    report_case: ReportCase | None = None,
    step: StepTask | None = None,
) -> tuple[SkillRun, bool]:
    run, created = await create_skill_run(
        db,
        skill_version_id=version_id,
        idempotency_key=idempotency_key,
        input_snapshot=_safe_input_snapshot(input_data),
        context_snapshot=_safe_input_snapshot(input_data),
        run_type="EVALUATION" if report_case is None else "INITIAL",
        target_type=target_type,
        target_key=target_key,
        report_case_id=report_case.id if report_case else None,
        workflow_instance_id=report_case.workflow_instance_id if report_case else None,
        step_task_id=step.id if step else None,
        runtime_instruction=runtime_instruction,
    )
    if created:
        event = WorkflowOutbox(
            aggregate_type="skill_run",
            aggregate_id=run.id,
            event_type="skill.run.requested",
            payload_json={"skill_run_id": run.id},
            status="PENDING",
            retry_count=0,
            created_at=datetime.utcnow(),
        )
        db.add(event)
        await db.flush()
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        existing = await db.scalar(
            select(SkillRun).where(SkillRun.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise
        if (
            existing.skill_version_id != version_id
            or existing.report_case_id != (report_case.id if report_case else None)
            or existing.target_type != target_type
            or existing.target_key != target_key
        ):
            raise ValueError("skill_run_idempotency_conflict")
        return existing, False
    await db.refresh(run)
    return run, created


async def queue_debug_skill_run(
    db: AsyncSession,
    *,
    version_id: int,
    idempotency_key: str,
    input_data: dict[str, Any],
    runtime_instruction: str | None,
) -> tuple[SkillRun, bool]:
    return await _queue_run(
        db,
        version_id=version_id,
        idempotency_key=idempotency_key,
        input_data=input_data,
        runtime_instruction=runtime_instruction,
        target_type="DEBUG",
        target_key=f"skill-version:{version_id}",
    )


async def queue_case_step_skill_run(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    actor: User,
    idempotency_key: str,
    runtime_instruction: str | None,
) -> tuple[SkillRun, bool]:
    report_case = await _authorize_case(db, case_id, actor)
    if report_case.workflow_instance_id is None:
        raise ValueError("workflow_instance_not_found")
    step = await db.scalar(
        select(StepTask).where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == step_key,
        )
    )
    if step is None:
        raise ValueError("step_task_not_found")
    if step.status not in {"READY", "IN_REVIEW", "NEEDS_REVISION"}:
        raise ValueError("step_not_ready")
    if actor.role == "consultant" and step.assignee_id not in (None, actor.id):
        raise ValueError("step_assigned_to_another_consultant")
    version_id = (step.config_snapshot or {}).get("skill_version_id")
    if step.executor not in {"AI", "HYBRID"} or not version_id:
        raise ValueError("step_skill_not_configured")
    version = await db.get(AISkillVersion, version_id)
    if version is None or version.status != "PUBLISHED":
        raise ValueError("step_skill_version_unavailable")
    return await _queue_run(
        db,
        version_id=version.id,
        idempotency_key=idempotency_key,
        input_data=report_case.application_snapshot or {},
        runtime_instruction=runtime_instruction,
        target_type="REPORT_CASE_STEP",
        target_key=step.step_key,
        report_case=report_case,
        step=step,
    )


async def list_case_skill_runs(
    db: AsyncSession, *, case_id: int, actor: User
) -> list[SkillRun]:
    await _authorize_case(db, case_id, actor)
    result = await db.scalars(
        select(SkillRun)
        .where(SkillRun.report_case_id == case_id)
        .order_by(SkillRun.created_at.desc(), SkillRun.id.desc())
    )
    return list(result.all())


async def execute_skill_run_record(
    db: AsyncSession,
    run_id: int,
    *,
    gateway: ModelGateway | None = None,
) -> SkillRun:
    run = await db.scalar(
        select(SkillRun).where(SkillRun.id == run_id).with_for_update()
    )
    if run is None:
        raise ValueError("skill_run_not_found")
    if run.status == "COMPLETED":
        return run
    if run.status == "RUNNING":
        return run
    if run.status != "PENDING":
        return run
    skill_version = await db.get(AISkillVersion, run.skill_version_id)
    if skill_version is None:
        run.status = "FAILED"
        run.error = "skill_version_not_found"
        run.completed_at = datetime.utcnow()
        await db.commit()
        return run
    run.status = "RUNNING"
    run.started_at = datetime.utcnow()
    await db.commit()
    try:
        result = await execute_skill(
            skill_version=skill_version,
            input_data=run.input_snapshot or {},
            runtime_instruction=run.runtime_instruction,
            gateway=gateway or DeepSeekGateway(),
        )
        run.output_raw = result.output_raw
        run.output_parsed = result.output_parsed
        run.context_snapshot = result.context_snapshot
        run.model_trace = result.model_trace
        run.status = "COMPLETED"
        run.error = None
    except SkillExecutionError as error:
        run.status = "FAILED"
        run.error = str(error)
        run.model_trace = error.model_trace
    except Exception as error:
        run.status = "FAILED"
        run.error = (
            str(error) if isinstance(error, ValueError) else type(error).__name__
        )
    run.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(run)
    return run
