from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from copy import deepcopy
from app.domains.content.product_framework import framework_snapshot
from app.domains.content.reasoning_contract import reasoning_snapshot
from app.domains.skills.bindings import freeze_report_skills

from .definitions import validate_workflow_definition
from .models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowOutbox,
    WorkflowVersion,
)
from app.core.time import utc_now_naive


def _now() -> datetime:
    return utc_now_naive()


async def latest_published_version(
    db: AsyncSession, workflow_key: str = "report.production"
) -> Optional[WorkflowVersion]:
    result = await db.execute(
        select(WorkflowVersion)
        .where(
            WorkflowVersion.workflow_key == workflow_key,
            WorkflowVersion.status == "PUBLISHED",
        )
        .order_by(WorkflowVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_workflow_draft(
    db: AsyncSession,
    workflow_key: str,
    name: str,
    definition: dict[str, Any],
    created_by: Optional[int],
) -> WorkflowVersion:
    normalized = validate_workflow_definition(definition)
    latest_version = await db.scalar(
        select(func.max(WorkflowVersion.version)).where(
            WorkflowVersion.workflow_key == workflow_key
        )
    )
    now = _now()
    version = WorkflowVersion(
        workflow_key=workflow_key,
        name=name,
        version=(latest_version or 0) + 1,
        status="DRAFT",
        definition_json=normalized,
        created_by=created_by,
        created_at=now,
    )
    db.add(version)
    await db.flush()
    return version


async def publish_workflow_version(
    db: AsyncSession, version_id: int, published_by: Optional[int]
) -> WorkflowVersion:
    version = await db.scalar(
        select(WorkflowVersion)
        .where(WorkflowVersion.id == version_id)
        .with_for_update()
    )
    if version is None:
        raise ValueError("workflow_version_not_found")
    if version.status != "DRAFT":
        raise ValueError("workflow_version_immutable")
    version.definition_json = validate_workflow_definition(version.definition_json)
    if version.workflow_key == "report.production":
        version.definition_json = {**version.definition_json, "skill_bindings":
            await freeze_report_skills(db, version.definition_json.get("skill_bindings"),
                                      version.definition_json["steps"])}
    version.status = "PUBLISHED"
    version.published_by = published_by
    version.published_at = _now()
    await db.flush()
    return version


async def enqueue_outbox_event(
    db: AsyncSession,
    *,
    aggregate_type: str,
    aggregate_id: int,
    event_type: str,
    payload: dict[str, Any],
) -> WorkflowOutbox:
    event = WorkflowOutbox(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        event_type=event_type,
        payload_json=payload,
        status="PENDING",
        retry_count=0,
        created_at=_now(),
    )
    db.add(event)
    await db.flush()
    return event


async def create_report_case(
    db: AsyncSession,
    *,
    user_id: int,
    service_request_id: Optional[int],
    source_report_task_id: Optional[str],
    application_snapshot: dict[str, Any],
    workflow_version: Optional[WorkflowVersion] = None,
) -> ReportCase:
    if service_request_id is not None:
        existing = await db.scalar(
            select(ReportCase).where(
                ReportCase.service_request_id == service_request_id
            )
        )
        if existing:
            return existing
    if source_report_task_id is not None:
        existing = await db.scalar(
            select(ReportCase).where(
                ReportCase.source_report_task_id == source_report_task_id
            )
        )
        if existing:
            return existing

    version = workflow_version or await latest_published_version(db)
    if version is None:
        raise ValueError("workflow_version_not_published")

    now = _now()
    frozen_application = deepcopy(application_snapshot)
    # The chosen workflow is frozen into the case snapshot at creation time.
    # Cases never switch workflows halfway through, so the stored key is the
    # only value later readers and writers should trust.
    frozen_application["workflow_key"] = version.workflow_key
    collaboration = version.definition_json.get("collaboration_contract")
    if collaboration:
        frozen_application["collaboration_contract"] = deepcopy(collaboration)
    if version.workflow_key == "report.production":
        # Only newly created production cases opt in. Existing cases are never rewritten.
        frozen_application["framework_contract"] = framework_snapshot()
        frozen_application["reasoning_contract"] = reasoning_snapshot()
        frozen_application["skill_bindings"] = await freeze_report_skills(
            db, version.definition_json.get("skill_bindings"), version.definition_json["steps"])
    report_case = ReportCase(
        user_id=user_id,
        service_request_id=service_request_id,
        source_report_task_id=source_report_task_id,
        status="ACTIVE",
        application_snapshot=frozen_application,
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(report_case)
    await db.flush()

    instance = WorkflowInstance(
        report_case_id=report_case.id,
        workflow_version_id=version.id,
        status="RUNNING",
        created_at=now,
        updated_at=now,
        started_at=now,
    )
    db.add(instance)
    await db.flush()

    steps = version.definition_json["steps"]
    task_by_key: dict[str, StepTask] = {}
    for index, step in enumerate(steps):
        is_first = index == 0
        task = StepTask(
            workflow_instance_id=instance.id,
            step_key=step["step_key"],
            sequence_no=step["sequence_no"],
            executor=step["executor"],
            status="READY" if is_first else "PENDING",
            # The published workflow version freezes the professional owner for
            # this case. Do not silently replace it with the latest code mapping.
            required_capability=step.get("required_capability"),
            activation_no=1 if is_first else 0,
            config_snapshot=step.get("config", {}),
            activated_at=now if is_first else None,
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        task_by_key[task.step_key] = task
    await db.flush()

    report_case.workflow_instance_id = instance.id
    report_case.updated_at = now
    first_task = task_by_key[steps[0]["step_key"]]
    await enqueue_outbox_event(
        db,
        aggregate_type="workflow_instance",
        aggregate_id=instance.id,
        event_type="workflow.step.ready",
        payload={
            "report_case_id": report_case.id,
            "workflow_instance_id": instance.id,
            "step_task_id": first_task.id,
            "step_key": first_task.step_key,
            "activation_no": first_task.activation_no,
        },
    )
    await enqueue_outbox_event(
        db,
        aggregate_type="report_case",
        aggregate_id=report_case.id,
        event_type="report_case.created",
        payload={"report_case_id": report_case.id, "workflow_instance_id": instance.id},
    )
    await db.flush()
    return report_case


class CompletionGate:
    """V1 manual gate: only the active step can complete after review starts."""

    @staticmethod
    def validate(step: StepTask, ordered_steps: list[StepTask]) -> None:
        if step.status != "IN_REVIEW":
            raise ValueError("step_not_in_review")
        if any(
            previous.sequence_no < step.sequence_no and previous.status != "COMPLETED"
            for previous in ordered_steps
        ):
            raise ValueError("workflow_step_order_invalid")
        policy = (step.config_snapshot or {}).get("completion_policy", "MANUAL")
        if policy != "MANUAL":
            raise ValueError("workflow_completion_policy_unsupported")


async def _lock_case_and_tasks(
    db: AsyncSession, case_id: int
) -> tuple[ReportCase, WorkflowInstance, list[StepTask]]:
    report_case = await db.scalar(
        select(ReportCase).where(ReportCase.id == case_id).with_for_update()
    )
    if report_case is None:
        raise ValueError("report_case_not_found")
    if report_case.workflow_instance_id is None:
        raise ValueError("workflow_instance_not_found")
    instance = await db.scalar(
        select(WorkflowInstance)
        .where(WorkflowInstance.id == report_case.workflow_instance_id)
        .with_for_update()
    )
    if instance is None:
        raise ValueError("workflow_instance_not_found")
    result = await db.execute(
        select(StepTask)
        .where(StepTask.workflow_instance_id == instance.id)
        .order_by(StepTask.sequence_no)
        .with_for_update()
    )
    return report_case, instance, list(result.scalars().all())


def _find_step(tasks: list[StepTask], step_key: str) -> StepTask:
    for task in tasks:
        if task.step_key == step_key:
            return task
    raise ValueError("step_task_not_found")


async def lock_case_and_tasks(
    db: AsyncSession, case_id: int
) -> tuple[ReportCase, WorkflowInstance, list[StepTask]]:
    """Public accessor for case-level row locks shared by workflow use cases."""
    return await _lock_case_and_tasks(db, case_id)


async def start_step(db: AsyncSession, case_id: int, step_key: str) -> StepTask:
    report_case, instance, tasks = await _lock_case_and_tasks(db, case_id)
    task = _find_step(tasks, step_key)
    if instance.status != "RUNNING" or report_case.status in {"CANCELLED", "DELIVERED"}:
        raise ValueError("workflow_not_active")
    if task.status != "READY":
        raise ValueError("step_not_ready")
    if any(other.status == "IN_REVIEW" for other in tasks):
        raise ValueError("workflow_step_already_in_review")
    task.status = "IN_REVIEW"
    task.started_at = task.started_at or _now()
    task.updated_at = _now()
    await db.flush()
    return task


async def cancel_case(
    db: AsyncSession, case_id: int, *, reason: str = "request_closed"
) -> ReportCase:
    report_case, instance, tasks = await _lock_case_and_tasks(db, case_id)
    if report_case.status == "CANCELLED":
        return report_case
    if report_case.status == "DELIVERED":
        raise ValueError("workflow_case_already_delivered")
    now = _now()
    report_case.status = "CANCELLED"
    report_case.cancelled_at = now
    report_case.updated_at = now
    instance.status = "CANCELLED"
    instance.completed_at = None
    instance.suspended_at = None
    instance.updated_at = now
    for task in tasks:
        if task.status != "COMPLETED":
            task.status = "CANCELLED"
            task.updated_at = now
    await enqueue_outbox_event(
        db,
        aggregate_type="report_case",
        aggregate_id=report_case.id,
        event_type="report_case.cancelled",
        payload={
            "report_case_id": report_case.id,
            "workflow_instance_id": instance.id,
            "reason": reason[:1000],
        },
    )
    await db.flush()
    return report_case


async def complete_step(
    db: AsyncSession,
    case_id: int,
    step_key: str,
    *,
    result_json: Optional[dict[str, Any]] = None,
    final_gate_verified: bool = False,
) -> StepTask:
    report_case, instance, tasks = await _lock_case_and_tasks(db, case_id)
    task = _find_step(tasks, step_key)
    if instance.status != "RUNNING" or report_case.status in {"CANCELLED", "DELIVERED"}:
        raise ValueError("workflow_not_active")
    CompletionGate.validate(task, tasks)
    if (
        task.step_key == "S6" or (task.config_snapshot or {}).get("final_gate") is True
    ) and not final_gate_verified:
        raise ValueError("final_gate_approval_required")

    now = _now()
    task.status = "COMPLETED"
    task.result_json = result_json
    task.completed_at = now
    task.updated_at = now
    following = next(
        (item for item in tasks if item.sequence_no > task.sequence_no), None
    )
    if following is None:
        instance.status = "COMPLETED"
        instance.completed_at = now
        report_case.status = "READY_TO_DELIVER"
        await enqueue_outbox_event(
            db,
            aggregate_type="workflow_instance",
            aggregate_id=instance.id,
            event_type="workflow.completed",
            payload={
                "report_case_id": report_case.id,
                "workflow_instance_id": instance.id,
            },
        )
    else:
        if following.status != "PENDING":
            raise ValueError("workflow_next_step_not_pending")
        following.status = "READY"
        following.activation_no += 1
        following.activated_at = now
        following.updated_at = now
        report_case.status = "ACTIVE"
        await enqueue_outbox_event(
            db,
            aggregate_type="workflow_instance",
            aggregate_id=instance.id,
            event_type="workflow.step.ready",
            payload={
                "report_case_id": report_case.id,
                "workflow_instance_id": instance.id,
                "step_task_id": following.id,
                "step_key": following.step_key,
                "activation_no": following.activation_no,
            },
        )
    report_case.updated_at = now
    instance.updated_at = now
    await db.flush()
    return task


async def _rewind_to_step(
    db: AsyncSession,
    report_case: ReportCase,
    instance: WorkflowInstance,
    tasks: list[StepTask],
    target: StepTask,
    *,
    reason: Optional[str],
) -> StepTask:
    if instance.status == "CANCELLED" or report_case.status in {
        "CANCELLED",
        "DELIVERED",
    }:
        raise ValueError("workflow_not_active")
    if target.status not in {"COMPLETED", "NEEDS_REVISION"}:
        raise ValueError("step_cannot_reopen")
    now = _now()
    for task in tasks:
        if task.sequence_no > target.sequence_no:
            task.status = "PENDING"
            task.started_at = None
            task.completed_at = None
            task.activated_at = None
            task.updated_at = now
    target.status = "NEEDS_REVISION"
    target.activation_no += 1
    target.status = "READY"
    target.activated_at = now
    target.started_at = None
    target.completed_at = None
    target.updated_at = now
    if instance.status == "COMPLETED":
        instance.status = "RUNNING"
        instance.completed_at = None
    instance.updated_at = now
    report_case.status = "ACTIVE"
    report_case.updated_at = now
    await enqueue_outbox_event(
        db,
        aggregate_type="workflow_instance",
        aggregate_id=instance.id,
        event_type="workflow.step.returned" if reason else "workflow.step.reopened",
        payload={
            "report_case_id": report_case.id,
            "workflow_instance_id": instance.id,
            "step_task_id": target.id,
            "step_key": target.step_key,
            "activation_no": target.activation_no,
            "reason": reason,
        },
    )
    await enqueue_outbox_event(
        db,
        aggregate_type="workflow_instance",
        aggregate_id=instance.id,
        event_type="workflow.step.ready",
        payload={
            "report_case_id": report_case.id,
            "workflow_instance_id": instance.id,
            "step_task_id": target.id,
            "step_key": target.step_key,
            "activation_no": target.activation_no,
        },
    )
    await db.flush()
    return target


async def return_to_step(
    db: AsyncSession,
    case_id: int,
    current_step_key: str,
    target_step_key: str,
    reason: str,
) -> StepTask:
    report_case, instance, tasks = await _lock_case_and_tasks(db, case_id)
    current = _find_step(tasks, current_step_key)
    target = _find_step(tasks, target_step_key)
    if current.status != "IN_REVIEW":
        raise ValueError("step_not_in_review")
    if target.sequence_no >= current.sequence_no:
        raise ValueError("return_target_must_be_previous")
    current.status = "PENDING"
    current.started_at = None
    current.updated_at = _now()
    return await _rewind_to_step(
        db, report_case, instance, tasks, target, reason=reason.strip()
    )


async def reopen_step(db: AsyncSession, case_id: int, step_key: str) -> StepTask:
    report_case, instance, tasks = await _lock_case_and_tasks(db, case_id)
    target = _find_step(tasks, step_key)
    return await _rewind_to_step(db, report_case, instance, tasks, target, reason=None)


async def assign_step(
    db: AsyncSession, case_id: int, step_key: str, assignee_id: Optional[int]
) -> StepTask:
    report_case, _, tasks = await _lock_case_and_tasks(db, case_id)
    if report_case.status in {"CANCELLED", "DELIVERED"}:
        raise ValueError("workflow_not_active")
    task = _find_step(tasks, step_key)
    from app.models.user import User
    from app.domains.service_requests.models import ServiceRequest
    from .authorization import SPECIALTY_FIELDS, consultant_capabilities
    if task.required_capability in SPECIALTY_FIELDS:
        assignee = await db.get(User, assignee_id) if assignee_id is not None else None
        if assignee_id is not None and (
            assignee is None
            or assignee.role != "consultant"
            or not assignee.is_active
            or task.required_capability not in consultant_capabilities(assignee)
        ):
            raise ValueError("step_specialty_required")
        affected = [item for item in tasks if item.required_capability == task.required_capability]
        if any(item.status in {"IN_REVIEW", "COMPLETED"} and item.assignee_id != assignee_id for item in affected):
            raise ValueError("step_assignment_locked")
        request = await db.get(ServiceRequest, report_case.service_request_id)
        if request:
            setattr(request, SPECIALTY_FIELDS[task.required_capability], assignee_id)
            request.assigned_consultant_id = request.assigned_mingli_consultant_id or request.assigned_psychology_consultant_id
        for item in affected:
            item.assignee_id = assignee_id
    task.assignee_id = assignee_id
    task.updated_at = _now()
    await db.flush()
    return task
