from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession
from copy import deepcopy
from app.domains.content.product_framework import framework_snapshot
from app.domains.content.reasoning_contract import reasoning_snapshot
from app.domains.delivery.simple_models import SimpleStepExecution
from app.domains.skills.bindings import freeze_report_skills
from app.domains.skills.models import SkillRun

from .definitions import SIMPLE_WORKFLOW_KEY, validate_workflow_definition
from .simple_definitions import (
    SIMPLE_PROTOCOL_AI_ASSISTED,
    SIMPLE_PROTOCOL_LEGACY,
    case_simple_protocol,
    simple_ai_required_skill_keys,
    simple_protocol_from_definition,
)
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


async def enqueue_step_ready(
    db: AsyncSession, report_case: ReportCase, step: StepTask
) -> WorkflowOutbox:
    """Queue the single "this step may start now" event for a case step."""
    return await enqueue_outbox_event(
        db,
        aggregate_type="workflow_instance",
        aggregate_id=step.workflow_instance_id,
        event_type="workflow.step.ready",
        payload={
            "report_case_id": report_case.id,
            "workflow_instance_id": step.workflow_instance_id,
            "step_task_id": step.id,
            "step_key": step.step_key,
            "activation_no": step.activation_no,
        },
    )


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
    simple_protocol: Optional[str] = None
    if version.workflow_key == SIMPLE_WORKFLOW_KEY:
        # Simple freezes its execution protocol on the case so a later code
        # deployment cannot silently switch an existing case between the
        # legacy manual protocol and the AI-assisted protocol.
        simple_protocol = simple_protocol_from_definition(version.definition_json)
        if (
            simple_protocol != SIMPLE_PROTOCOL_LEGACY
            or "simple_protocol" in version.definition_json
        ):
            frozen_application["simple_protocol"] = simple_protocol
        if simple_protocol == SIMPLE_PROTOCOL_AI_ASSISTED:
            # AI-assisted cases reuse the production skills, but only the six
            # business skills their frozen definition declares.  The narrative
            # plan skill belongs to the standard workflow and is never bound.
            frozen_application["skill_bindings"] = await freeze_report_skills(
                db,
                version.definition_json.get("skill_bindings"),
                version.definition_json["steps"],
                required_keys=simple_ai_required_skill_keys(
                    version.definition_json
                ),
            )
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
        review_policy_version="six-node-review-v1" if version.workflow_key == "report.production" else None,
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
        config_snapshot = deepcopy(step.get("config", {}))
        if simple_protocol == SIMPLE_PROTOCOL_AI_ASSISTED:
            # Pin the frozen skill version on the step so the run entry point
            # never re-resolves a newer published skill for a frozen case.
            skill_key = config_snapshot.get("skill_key")
            binding = (frozen_application.get("skill_bindings") or {}).get(
                skill_key
            )
            if not isinstance(binding, dict) or not isinstance(
                binding.get("id"), int
            ):
                raise ValueError("case_skill_bindings_incomplete")
            config_snapshot["skill_version_id"] = binding["id"]
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
            config_snapshot=config_snapshot,
            activated_at=now if is_first else None,
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        task_by_key[task.step_key] = task
    await db.flush()

    if simple_protocol == SIMPLE_PROTOCOL_AI_ASSISTED:
        # Every business step gets one execution row up front.  Steps that are
        # not activated yet keep a placeholder activation of 1; activation and
        # reopen copy the execution counter onto the step task so both rows
        # always agree once a step is live.
        for step in steps:
            task = task_by_key[step["step_key"]]
            db.add(
                SimpleStepExecution(
                    report_case_id=report_case.id,
                    step_task_id=task.id,
                    step_key=task.step_key,
                    execution_status="READY",
                    dependency_status="CURRENT",
                    activation_no=max(task.activation_no, 1),
                    current_revision_id=None,
                    confirmed_revision_id=None,
                    active_skill_run_id=None,
                    input_snapshot={},
                    input_fingerprint=None,
                    stale_reason=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        await db.flush()

    report_case.workflow_instance_id = instance.id
    report_case.updated_at = now
    first_task = task_by_key[steps[0]["step_key"]]
    if simple_protocol != SIMPLE_PROTOCOL_AI_ASSISTED:
        # AI-assisted cases wait for a consultant: the first generation starts
        # when the request is accepted or assigned, never at creation time.
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
    if task.status == "IN_REVIEW":
        # 上游成果就绪后，后台准备流程会直接开始节点；重复或稍晚的“开始”请求
        # 视为已开始，避免咨询师看到“请刷新后重试”的假失败。
        return task
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


async def _sync_simple_execution_activation(
    db: AsyncSession, report_case: ReportCase, step: StepTask
) -> None:
    """Keep the AI Simple execution counter aligned with its step task."""
    if case_simple_protocol(report_case) != SIMPLE_PROTOCOL_AI_ASSISTED:
        return
    execution = await db.scalar(
        select(SimpleStepExecution).where(
            SimpleStepExecution.report_case_id == report_case.id,
            SimpleStepExecution.step_key == step.step_key,
        )
    )
    if execution is None:
        return
    execution.activation_no = step.activation_no
    execution.updated_at = _now()


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
    if report_case.review_policy_version == "six-node-review-v1":
        from app.domains.review.models import NodeApproval
        approval = await db.get(NodeApproval, (result_json or {}).get("node_approval_id")) if (result_json or {}).get("node_approval_id") else None
        if not approval or approval.report_case_id != case_id or approval.step_task_id != task.id or approval.activation_no != task.activation_no:
            raise ValueError("node_whole_review_required")
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
        await _sync_simple_execution_activation(db, report_case, following)
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


async def _prepare_simple_reassignment(
    db: AsyncSession,
    report_case: ReportCase,
    task: StepTask,
    *,
    previous_assignee_id: Optional[int],
    assignee_id: Optional[int],
) -> None:
    """Invalidate the previous owner's in-flight Simple run, if any."""
    if (
        previous_assignee_id == assignee_id
        or case_simple_protocol(report_case) != SIMPLE_PROTOCOL_AI_ASSISTED
        or task.status not in {"READY", "EXECUTING", "IN_REVIEW"}
    ):
        return
    execution = await db.scalar(
        select(SimpleStepExecution)
        .where(
            SimpleStepExecution.report_case_id == report_case.id,
            SimpleStepExecution.step_key == task.step_key,
        )
        .with_for_update()
    )
    if execution is None:
        return
    now = _now()
    if execution.execution_status in {"GENERATING", "REVISING"}:
        if execution.active_skill_run_id is not None:
            run = await db.get(SkillRun, execution.active_skill_run_id)
            if run is not None:
                context = dict(run.context_snapshot or {})
                context["simple_archived"] = "assignee_reassigned"
                run.context_snapshot = context
                flag_modified(run, "context_snapshot")
        execution.execution_status = "FAILED"
        execution.active_skill_run_id = None
        execution.input_fingerprint = None
        execution.input_snapshot = {
            **(execution.input_snapshot or {}),
            "last_error": "simple_assignee_changed",
        }
        execution.updated_at = now
        flag_modified(execution, "input_snapshot")
        task.status = "READY"
        task.started_at = None
        task.last_error = "simple_assignee_changed"
        task.updated_at = now
        return
    if execution.execution_status == "FAILED":
        task.status = "READY"
        task.last_error = "simple_assignee_changed"
        task.updated_at = now
    elif execution.execution_status == "IN_REVIEW":
        task.status = "IN_REVIEW"
        task.updated_at = now


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
    previous_assignee_id = task.assignee_id
    simple_ai = case_simple_protocol(report_case) == SIMPLE_PROTOCOL_AI_ASSISTED
    if task.required_capability in SPECIALTY_FIELDS and not simple_ai:
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
    await _prepare_simple_reassignment(
        db,
        report_case,
        task,
        previous_assignee_id=previous_assignee_id,
        assignee_id=assignee_id,
    )
    task.assignee_id = assignee_id
    task.updated_at = _now()
    if assignee_id is not None and report_case.review_policy_version == "six-node-review-v1":
        for item in tasks:
            if item.status == "READY" and item.assignee_id is not None:
                await enqueue_outbox_event(db, aggregate_type="workflow_instance", aggregate_id=item.workflow_instance_id,
                    event_type="workflow.step.ready", payload={"report_case_id": case_id, "step_task_id": item.id, "activation_no": item.activation_no})
    if (
        assignee_id is not None
        and simple_ai
        and task.status == "READY"
    ):
        # AI-assisted Simple starts generating as soon as an assignee owns the
        # activated step.  Re-assignment never rewrites earlier revisions; the
        # in-flight run is invalidated by the activation/owner check instead.
        await enqueue_step_ready(db, report_case, task)
    await db.flush()
    return task
