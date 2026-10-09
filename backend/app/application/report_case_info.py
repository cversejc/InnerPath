"""Consultant questions and user-provided follow-up evidence for report cases."""

from copy import deepcopy
from datetime import datetime
from app.core.time import utc_now_naive

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.domains.content.evidence import create_evidence_item
from app.domains.service_requests.models import ServiceRequest
from app.domains.service_requests.repository import _append_revision
from app.domains.skills.models import SkillRun
from app.domains.workflow.authorization import validate_step_actor
from app.domains.workflow.models import ReportCase, StepTask, WorkflowInstance
from app.models.user import User


async def request_report_case_info(
    db: AsyncSession,
    *,
    report_case_id: int,
    step_key: str,
    actor: User,
    reason: str,
    audit_context: AuditContext | None = None,
) -> ServiceRequest:
    report_case = await db.scalar(
        select(ReportCase).where(ReportCase.id == report_case_id).with_for_update()
    )
    if report_case is None:
        raise ValueError("report_case_not_found")
    if report_case.service_request_id is None:
        raise ValueError("report_case_user_request_required")
    request = await db.scalar(
        select(ServiceRequest)
        .where(ServiceRequest.id == report_case.service_request_id)
        .with_for_update()
    )
    instance = await db.scalar(
        select(WorkflowInstance)
        .where(WorkflowInstance.id == report_case.workflow_instance_id)
        .with_for_update()
    )
    if request is None or instance is None:
        raise ValueError("report_case_not_found")
    step = await db.scalar(
        select(StepTask)
        .where(
            StepTask.workflow_instance_id == instance.id,
            StepTask.step_key == step_key,
        )
        .with_for_update()
    )
    if step is None:
        raise ValueError("step_task_not_found")
    validate_step_actor(step, actor)
    active_step = await db.scalar(
        select(StepTask)
        .where(
            StepTask.workflow_instance_id == instance.id,
            StepTask.status.in_({"READY", "IN_REVIEW", "EXECUTING", "WAITING_REVIEW"}),
        )
        .order_by(StepTask.sequence_no)
        .limit(1)
    )
    if active_step is None or active_step.id != step.id:
        raise ValueError("step_not_current")
    if step.status != "IN_REVIEW":
        raise ValueError("step_not_in_review")
    if (
        report_case.status != "ACTIVE"
        or instance.status != "RUNNING"
        or request.status != "accepted"
    ):
        raise ValueError("report_case_info_request_not_allowed")

    active_run_id = await db.scalar(
        select(SkillRun.id)
        .where(
            SkillRun.report_case_id == report_case.id,
            SkillRun.step_task_id == step.id,
            SkillRun.status.in_({"PENDING", "RUNNING"}),
        )
        .limit(1)
        .with_for_update()
    )
    if active_run_id is not None:
        raise ValueError("report_case_skill_run_in_progress")

    clean_reason = reason.strip()
    if not clean_reason:
        raise ValueError("report_case_info_reason_required")
    await _append_revision(
        db,
        request.id,
        "report_case_info_requested",
        {
            "request_payload": deepcopy(request.request_payload or {}),
            "report_case_id": report_case.id,
            "step_key": step.step_key,
            "question": clean_reason,
        },
        actor.id,
    )
    request.status = "needs_info"
    request.needs_info_reason = clean_reason
    request.needs_info_at = request.updated_at = utc_now_naive()
    request.updated_by = actor.id
    report_case.status = "BLOCKED"
    report_case.updated_at = request.updated_at
    instance.status = "SUSPENDED"
    instance.suspended_at = instance.updated_at = request.updated_at
    await record_audit(
        db,
        actor.id,
        "report_case.info_requested",
        "report_case",
        str(report_case.id),
        target_user_id=report_case.user_id,
        details={"step_key": step.step_key, "question_provided": True},
        audit_context=audit_context,
    )
    await db.commit()
    await db.refresh(request)
    return request


async def submit_report_case_supplement(
    db: AsyncSession,
    *,
    report_case_id: int,
    user: User,
    response_key: str,
    answer: str,
    audit_context: AuditContext | None = None,
) -> dict:
    report_case = await db.scalar(
        select(ReportCase).where(ReportCase.id == report_case_id).with_for_update()
    )
    if report_case is None or report_case.user_id != user.id:
        raise ValueError("report_case_not_found")
    if report_case.service_request_id is None:
        raise ValueError("report_case_user_request_required")
    request = await db.scalar(
        select(ServiceRequest)
        .where(ServiceRequest.id == report_case.service_request_id)
        .with_for_update()
    )
    instance = await db.scalar(
        select(WorkflowInstance)
        .where(WorkflowInstance.id == report_case.workflow_instance_id)
        .with_for_update()
    )
    if request is None or instance is None or request.user_id != user.id:
        raise ValueError("report_case_not_found")

    payload = deepcopy(request.request_payload or {})
    responses = list(payload.get("report_case_supplements") or [])
    existing = next(
        (item for item in responses if item.get("response_key") == response_key), None
    )
    if existing:
        if existing.get("answer") != answer.strip():
            raise ValueError("report_case_supplement_idempotency_conflict")
        return {
            "report_case_id": report_case.id,
            "service_request_id": request.id,
            "evidence_key": existing["evidence_key"],
            "step_key": existing["step_key"],
            "status": request.status,
        }

    if (
        request.status != "needs_info"
        or not request.needs_info_reason
        or report_case.status != "BLOCKED"
        or instance.status != "SUSPENDED"
    ):
        raise ValueError("report_case_not_waiting_for_user_info")
    clean_answer = answer.strip()
    if not clean_answer:
        raise ValueError("report_case_supplement_required")
    active_step = await db.scalar(
        select(StepTask)
        .where(
            StepTask.workflow_instance_id == instance.id,
            StepTask.status == "IN_REVIEW",
        )
        .order_by(StepTask.sequence_no)
        .limit(1)
    )
    if active_step is None:
        raise ValueError("report_case_waiting_step_missing")

    cycle = len(responses) + 1
    evidence_key = f"user.follow_up.{cycle:03d}"
    question = request.needs_info_reason
    active_step.activation_no += 1
    active_step.updated_at = utc_now_naive()
    response = {
        "response_key": response_key,
        "cycle": cycle,
        "step_key": active_step.step_key,
        "question": question,
        "answer": clean_answer,
        "evidence_key": evidence_key,
    }
    await create_evidence_item(
        db,
        report_case_id=report_case.id,
        evidence_key=evidence_key,
        source_type="USER_PROVIDED",
        source_ref=f"service_request:{request.id}:follow_up:{cycle}",
        value={"question": question, "answer": clean_answer, "step_key": active_step.step_key},
        created_by=user.id,
    )
    responses.append(response)
    payload["report_case_supplements"] = responses
    await _append_revision(
        db,
        request.id,
        "report_case_supplement",
        deepcopy(payload),
        user.id,
    )
    request.request_payload = payload
    request.status = "accepted"
    request.needs_info_reason = None
    request.updated_by = user.id
    request.updated_at = utc_now_naive()
    report_case.status = "ACTIVE"
    report_case.updated_at = request.updated_at
    instance.status = "RUNNING"
    instance.suspended_at = None
    instance.updated_at = request.updated_at
    if report_case.review_policy_version == "six-node-review-v1":
        from app.domains.workflow.service import enqueue_outbox_event
        await enqueue_outbox_event(db, aggregate_type="report_case", aggregate_id=report_case.id, event_type="report.node.prepare", payload={"report_case_id": report_case.id, "step_task_id": active_step.id, "activation_no": active_step.activation_no})
    await record_audit(
        db,
        user.id,
        "report_case.info_answered",
        "report_case",
        str(report_case.id),
        target_user_id=user.id,
        details={
            "step_key": active_step.step_key,
            "activation_no": active_step.activation_no,
            "evidence_key": evidence_key,
            "answer_provided": True,
        },
        audit_context=audit_context,
    )
    await db.commit()
    return {
        "report_case_id": report_case.id,
        "service_request_id": request.id,
        "evidence_key": evidence_key,
        "step_key": active_step.step_key,
        "status": request.status,
    }
