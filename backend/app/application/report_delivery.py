from app.domains.workflow.authorization import validate_step_actor
from copy import deepcopy
from datetime import datetime
from app.core.time import api_datetime, utc_now_naive, utc_now_iso
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.report_quality import (
    case_can_be_delivered,
    delivery_quality_snapshot,
)
from app.application.workflow_commands import complete_case_step
from app.domains.audit.context import AuditContext
from app.domains.audit.service import record_audit
from app.domains.content.models import NarrativePlan
from app.domains.delivery.assembler import assemble_report_version
from app.domains.delivery.models import ReportVersion
from app.domains.quality.service import latest_validator_run
from app.domains.reports.models import Report
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.service_requests.models import ServiceRequest
from app.domains.users.lunar_calendar import solar_date_for_birth
from app.domains.workflow.models import ReportCase, StepTask, WorkflowInstance
from app.models.user import User


async def snapshot_case_skill_runs(
    db: AsyncSession, report_case_id: int
) -> list[dict]:
    runs = await db.scalars(
        select(SkillRun)
        .where(SkillRun.report_case_id == report_case_id)
        .order_by(SkillRun.id)
    )
    snapshots = []
    for run in runs:
        skill_version = await db.get(AISkillVersion, run.skill_version_id)
        snapshots.append(
            {
                "id": run.id,
                "skill_version": (
                    {
                        "id": skill_version.id,
                        "skill_key": skill_version.skill_key,
                        "name": skill_version.name,
                        "category": skill_version.category,
                        "version": skill_version.version,
                        "specification_json": deepcopy(skill_version.specification_json),
                    }
                    if skill_version
                    else {"id": run.skill_version_id}
                ),
                "workflow_instance_id": run.workflow_instance_id,
                "step_task_id": run.step_task_id,
                "target_type": run.target_type,
                "target_key": run.target_key,
                "run_type": run.run_type,
                "status": run.status,
                "runtime_instruction": run.runtime_instruction,
                "input_snapshot": deepcopy(run.input_snapshot or {}),
                "context_snapshot": deepcopy(run.context_snapshot or {}),
                "output_raw": run.output_raw,
                "output_parsed": deepcopy(run.output_parsed),
                "selected_examples": deepcopy(run.selected_examples or []),
                "selected_knowledge": deepcopy(run.selected_knowledge or []),
                "model_trace": deepcopy(run.model_trace or {}),
                "error": run.error,
                "retry_count": run.retry_count,
                "created_at": api_datetime(run.created_at),
                "started_at": api_datetime(run.started_at),
                "completed_at": api_datetime(run.completed_at),
            }
        )
    return snapshots


async def approve_case_final_gate(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    actor: User,
    note: Optional[str] = None,
    audit_context: Optional[AuditContext] = None,
    commit: bool = True,
) -> StepTask:
    if report_case.status in {"DELIVERED", "CANCELLED"}:
        raise ValueError("workflow_not_active")
    step = await db.scalar(
        select(StepTask)
        .where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == "S6",
        )
        .with_for_update()
    )
    if step is None:
        raise ValueError("step_task_not_found")
    if step.status != "IN_REVIEW":
        raise ValueError("step_not_in_review")
    validate_step_actor(step, actor)
    run = await latest_validator_run(db, report_case.id)
    if run is None or run.status != "COMPLETED":
        raise ValueError("final_qa_not_complete")
    if not await case_can_be_delivered(db, report_case):
        raise ValueError("final_qa_issues_open_or_stale")
    result = {
        "final_gate_approved": True,
        "validator_run_id": run.id,
        "qa_fingerprint": (run.context_snapshot or {}).get("qa_fingerprint"),
        "attested_by": actor.id,
        "attested_at": utc_now_iso(),
        "note": (note or "").strip() or None,
    }
    if report_case.review_policy_version == "six-node-review-v1":
        from app.domains.review.models import NodeApproval
        approval = await db.scalar(select(NodeApproval).where(NodeApproval.report_case_id == report_case.id, NodeApproval.step_task_id == step.id, NodeApproval.activation_no == step.activation_no).order_by(NodeApproval.id.desc()).limit(1))
        if not approval:
            raise ValueError("node_whole_review_required")
        result["node_approval_id"] = approval.id
    return await complete_case_step(
        db,
        actor.id,
        report_case.id,
        "S6",
        result,
        audit_context,
        final_gate_verified=True,
        commit=commit,
    )


async def deliver_report_case(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    actor: User,
    audit_context: Optional[AuditContext] = None,
    commit: bool = True,
) -> ReportVersion:
    locked_case = await db.scalar(
        select(ReportCase).where(ReportCase.id == report_case.id).with_for_update()
    )
    if locked_case is None:
        raise ValueError("report_case_not_found")
    if (locked_case.application_snapshot or {}).get("collaboration_contract"):
        final_step = await db.scalar(select(StepTask).where(
            StepTask.workflow_instance_id == locked_case.workflow_instance_id, StepTask.step_key == "S6"))
        if final_step is None:
            raise ValueError("step_task_not_found")
        validate_step_actor(final_step, actor)
    if locked_case.status == "DELIVERED":
        existing = await db.scalar(
            select(ReportVersion)
            .where(ReportVersion.report_case_id == locked_case.id)
            .order_by(ReportVersion.version_no.desc())
            .limit(1)
        )
        if existing:
            return existing
    if locked_case.status != "READY_TO_DELIVER":
        raise ValueError("workflow_not_ready_to_deliver")
    instance = await db.get(WorkflowInstance, locked_case.workflow_instance_id)
    gate = await db.scalar(
        select(StepTask).where(
            StepTask.workflow_instance_id == locked_case.workflow_instance_id,
            StepTask.step_key == "S6",
        )
    )
    if (
        instance is None
        or instance.status != "COMPLETED"
        or gate is None
        or gate.status != "COMPLETED"
        or not (gate.result_json or {}).get("final_gate_approved")
    ):
        raise ValueError("final_gate_approval_required")
    quality_snapshot = await delivery_quality_snapshot(db, locked_case)

    request = None
    if locked_case.service_request_id is not None:
        request = await db.scalar(
            select(ServiceRequest)
            .where(ServiceRequest.id == locked_case.service_request_id)
            .with_for_update()
        )
    skill_run_snapshot = await snapshot_case_skill_runs(db, locked_case.id)
    version = await assemble_report_version(
        db,
        locked_case,
        actor_id=actor.id,
        quality_snapshot=quality_snapshot,
        skill_run_snapshot=skill_run_snapshot,
    )
    await db.flush()
    snapshot = locked_case.application_snapshot or {}
    profile = snapshot.get("profile") or {}
    try:
        birth_date = solar_date_for_birth(
            int(profile["birth_year"]),
            int(profile["birth_month"]),
            int(profile["birth_day"]),
            calendar_type=profile.get("calendar_type", "solar"),
            is_leap_month=bool(profile.get("birth_is_leap_month", False)),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("report_profile_snapshot_invalid") from error
    sections = version.structured_data["structured_sections"]
    identity = "\n\n".join(
        item["content"] for item in sections if item["section_key"] == "identity"
    )
    challenge = "\n\n".join(
        item["content"] for item in sections if item["section_key"] == "challenge"
    )
    direction = "\n\n".join(
        item["content"] for item in sections if item["section_key"] == "direction"
    )
    summary = (version.structured_data.get("narrative_plan") or {}).get("core_theme")
    content_payload = {
        "report_version": {"id": version.id, "version_no": version.version_no},
        "structured_sections": sections,
        "summary": summary,
        "energy_profile": {
            "type": "人生说明书",
            "core_traits": summary or "咨询师确认内容",
            "description": identity,
        },
        "career_guidance": {
            "suitable_paths": [],
            "work_style": "",
            "development_suggestions": [direction] if direction else [],
        },
        "relationship_pattern": {
            "style": challenge,
            "strengths": [],
            "challenges": [],
            "growth_direction": direction,
        },
        "personal_growth": {"action_plan": []},
    }
    now = utc_now_naive()
    report = Report(
        user_id=locked_case.user_id,
        request_id=locked_case.service_request_id,
        title="辰鉴·人生说明书",
        birth_date=birth_date,
        birth_time=None,
        birth_calendar_type=profile.get("calendar_type", "solar"),
        birth_place=profile.get("birth_place"),
        input_snapshot={
            "service_type": "report",
            "name": profile.get("name") or "用户",
            **snapshot,
            "report_version": {"id": version.id, "version_no": version.version_no},
        },
        energy_profile=content_payload["energy_profile"],
        career_guidance=content_payload["career_guidance"],
        relationship_pattern=content_payload["relationship_pattern"],
        personal_growth=content_payload["personal_growth"],
        summary=summary,
        content_payload=content_payload,
        ai_raw_content=None,
        reviewed_by=actor.id,
        reviewed_at=now,
        additional_info=(snapshot.get("context") or {}).get("additional_info"),
        status="completed",
        is_deleted=False,
        created_at=now,
        updated_at=now,
    )
    db.add(report)
    await db.flush()
    locked_case.status = "DELIVERED"
    locked_case.delivered_at = now
    if request is not None:
        request.status = "delivered"
        request.result_type = "report"
        request.result_id = report.id
        request.delivered_at = now
        request.updated_by = actor.id
    await record_audit(
        db,
        actor.id,
        "report_case.deliver",
        "report_case",
        str(locked_case.id),
        target_user_id=locked_case.user_id,
        details={"report_version_id": version.id, "version_no": version.version_no, "report_id": report.id},
        audit_context=audit_context,
    )
    if commit:
        await db.commit()
        await db.refresh(version)
    return version


async def approve_and_deliver(db, case_id, actor, expected):
    """One lock and one commit; retries return the same immutable delivery."""
    from app.application.node_review_workspace import review_context
    from app.application.node_review_commands import sign_node
    case = await db.scalar(select(ReportCase).where(ReportCase.id == case_id).with_for_update())
    if not case:
        raise ValueError("report_case_not_found")
    if case.status == "DELIVERED":
        step = await db.scalar(select(StepTask).where(StepTask.workflow_instance_id == case.workflow_instance_id, StepTask.step_key == "S6"))
        validate_step_actor(step, actor)
        return await db.scalar(select(ReportVersion).where(ReportVersion.report_case_id == case_id).order_by(ReportVersion.version_no.desc()).limit(1))
    try:
        case, step, state = await review_context(db, case_id, "S6", actor, write=True)
        await sign_node(db, case, step, state, actor, expected)
        await approve_case_final_gate(db, report_case=case, actor=actor, commit=False)
        version = await deliver_report_case(db, report_case=case, actor=actor, commit=False)
        await db.commit()
        await db.refresh(version)
        return version
    except Exception:
        await db.rollback()
        raise
