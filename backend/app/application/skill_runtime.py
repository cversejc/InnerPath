from datetime import datetime
from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.domains.service_requests.models import ServiceRequest
from app.domains.content.service import create_evidence_item
from app.domains.content.fragments import create_content_fragment_revision
from app.domains.content.models import (
    CaseEvidenceItem,
    NarrativePlan,
)
from app.domains.content.narrative import (
    get_current_narrative_plan,
    semantic_source_snapshot,
)
from app.domains.content.queries import load_case_semantic_model
from app.domains.skills.definitions import (
    DEFAULT_SKILL_KEY,
    default_skill_specification,
)
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.runtime import (
    DeepSeekGateway,
    ModelGateway,
    SkillExecutionError,
    build_context_envelope,
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
from app.domains.quality.service import replace_validator_issues
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
    skill_version = await db.get(AISkillVersion, version_id)
    if skill_version is None:
        raise ValueError("skill_version_not_found")
    input_snapshot = build_context_envelope(
        input_data, skill_version.specification_json
    )
    context_snapshot = deepcopy(input_snapshot)
    semantic_sources = input_data.get("semantic_source_snapshot")
    if isinstance(semantic_sources, dict):
        context_snapshot["semantic_source_snapshot"] = semantic_sources
    narrative_plan_id = input_data.get("source_narrative_plan_id")
    if isinstance(narrative_plan_id, int):
        context_snapshot["source_narrative_plan_id"] = narrative_plan_id
    if report_case is not None:
        evidence_rows = await db.scalars(
            select(CaseEvidenceItem)
            .where(
                CaseEvidenceItem.report_case_id == report_case.id,
                CaseEvidenceItem.status == "ACTIVE",
            )
            .order_by(CaseEvidenceItem.evidence_key)
        )
        context_snapshot["source_references"] = {
            "evidence": [
                {
                    "evidence_id": item.id,
                    "evidence_key": item.evidence_key,
                    "source_type": item.source_type,
                    "source_ref": item.source_ref,
                    "source_skill_run_id": item.source_skill_run_id,
                }
                for item in evidence_rows
            ]
        }
    run, created = await create_skill_run(
        db,
        skill_version_id=version_id,
        idempotency_key=idempotency_key,
        input_snapshot=input_snapshot,
        context_snapshot=context_snapshot,
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


async def queue_case_authoring_skill_run(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    actor: User,
    skill_key: str,
    idempotency_key: str,
    runtime_instruction: str | None = None,
    fragment_key: str | None = None,
    fragment_title: str | None = None,
) -> tuple[SkillRun, bool]:
    report_case = await _authorize_case(db, case_id, actor)
    if report_case.workflow_instance_id is None:
        raise ValueError("workflow_instance_not_found")
    step = await db.scalar(
        select(StepTask)
        .where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == step_key,
        )
        .with_for_update()
    )
    if step is None:
        raise ValueError("step_task_not_found")
    if step_key != "S5" or step.status != "IN_REVIEW":
        raise ValueError("narrative_step_not_in_review")
    if actor.role == "consultant" and step.assignee_id not in (None, actor.id):
        raise ValueError("step_assigned_to_another_consultant")
    if skill_key not in {"report.narrative_plan", "report.fragment_authoring"}:
        raise ValueError("narrative_skill_unavailable")

    skill_version = await db.scalar(
        select(AISkillVersion)
        .where(
            AISkillVersion.skill_key == skill_key,
            AISkillVersion.status == "PUBLISHED",
        )
        .order_by(AISkillVersion.version.desc())
        .limit(1)
    )
    if skill_version is None:
        raise ValueError("narrative_skill_unavailable")

    semantic_model = await load_case_semantic_model(db, case_id)
    source_snapshot = semantic_source_snapshot(semantic_model)
    application_snapshot = _safe_input_snapshot(report_case.application_snapshot or {})
    context = dict(application_snapshot.get("context") or {})
    context["semantic_model"] = semantic_model
    input_data: dict[str, Any] = {
        **application_snapshot,
        "context": context,
        "semantic_source_snapshot": source_snapshot,
    }
    if skill_key == "report.narrative_plan":
        target_type = "NARRATIVE_CANDIDATES"
        target_key = step_key
    else:
        plan = await get_current_narrative_plan(db, case_id)
        if plan is None or plan.status != "CONFIRMED":
            raise ValueError("narrative_plan_confirmation_required")
        if plan.source_snapshot != source_snapshot:
            plan.status = "STALE"
            raise ValueError("narrative_semantics_changed")
        if not fragment_key or not fragment_key.strip():
            raise ValueError("report_fragment_key_invalid")
        context["narrative_plan"] = plan.plan_json
        context["narrative_plan_id"] = plan.id
        context["fragment_request"] = {
            "fragment_key": fragment_key.strip(),
            "title": (fragment_title or "").strip(),
        }
        input_data["source_narrative_plan_id"] = plan.id
        target_type = "REPORT_FRAGMENT"
        target_key = fragment_key.strip()

    return await _queue_run(
        db,
        version_id=skill_version.id,
        idempotency_key=idempotency_key,
        input_data=input_data,
        runtime_instruction=runtime_instruction,
        target_type=target_type,
        target_key=target_key,
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
        run.model_trace = result.model_trace
        prior_context = run.context_snapshot or {}
        source_references = deepcopy(prior_context.get("source_references") or {})
        run_metadata = {
            key: prior_context[key]
            for key in (
                "semantic_source_snapshot",
                "source_narrative_plan_id",
                "qa_fingerprint",
            )
            if key in prior_context
        }
        run.context_snapshot = {
            **result.context_snapshot,
            "source_references": source_references,
            **run_metadata,
        }
        if run.target_type == "REPORT_FRAGMENT":
            await _save_authored_report_fragment(db, run)
        elif run.target_type == "REPORT_QA":
            await replace_validator_issues(db, run)
        foundation = result.context_snapshot.get("foundation_data")
        if run.report_case_id is not None and foundation is not None:
            evidence = await create_evidence_item(
                db,
                report_case_id=run.report_case_id,
                evidence_key=f"calculated.foundation.skill_run.{run.id}",
                source_type="SYSTEM_CALCULATED",
                source_ref=f"skill_run:{run.id}:foundation_data",
                value=foundation,
                source_skill_run_id=run.id,
            )
            evidence_refs = list(source_references.get("evidence") or [])
            if not any(item.get("evidence_key") == evidence.evidence_key for item in evidence_refs):
                evidence_refs.append(
                    {
                        "evidence_id": evidence.id,
                        "evidence_key": evidence.evidence_key,
                        "source_type": evidence.source_type,
                        "source_ref": evidence.source_ref,
                        "source_skill_run_id": evidence.source_skill_run_id,
                    }
                )
            source_references["evidence"] = evidence_refs
        run.context_snapshot = {
            **result.context_snapshot,
            "source_references": source_references,
            **run_metadata,
        }
        flag_modified(run, "context_snapshot")
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


async def _save_authored_report_fragment(db: AsyncSession, run: SkillRun) -> None:
    output = run.output_parsed or {}
    if output.get("status") == "MISSING_SEMANTIC_SUPPORT":
        return
    if output.get("status") != "READY_FOR_REVIEW":
        raise ValueError("report_fragment_status_invalid")
    context = (run.context_snapshot or {}).get("context") or {}
    request = context.get("fragment_request") or {}
    plan_id = (run.context_snapshot or {}).get("source_narrative_plan_id")
    plan = await db.get(NarrativePlan, plan_id) if plan_id else None
    if plan is None or plan.status != "CONFIRMED":
        raise ValueError("narrative_plan_confirmation_required")
    semantic_model = context.get("semantic_model") or {}
    semantic_now = await load_case_semantic_model(db, run.report_case_id)
    if semantic_source_snapshot(semantic_now) != (run.context_snapshot or {}).get(
        "semantic_source_snapshot"
    ):
        raise ValueError("narrative_semantics_changed")
    if plan.source_snapshot != (run.context_snapshot or {}).get(
        "semantic_source_snapshot"
    ):
        raise ValueError("narrative_semantics_changed")

    used_findings = output.get("used_findings") or []
    used_fragments = output.get("used_analysis_fragments") or []
    evidence_refs = {
        key
        for item in semantic_model.get("findings", [])
        if item.get("finding_key") in used_findings
        for key in item.get("evidence_refs", [])
    }
    for item in semantic_model.get("analysis_fragments", []):
        if item.get("fragment_key") in used_fragments:
            evidence_refs.update(
                row.get("evidence_key")
                for row in (item.get("source_snapshot") or {}).get("evidence", [])
                if isinstance(row, dict) and row.get("evidence_key")
            )

    async with db.begin_nested():
        await create_content_fragment_revision(
            db,
            report_case_id=run.report_case_id,
            fragment_key=request.get("fragment_key") or run.target_key or "",
            fragment_type="REPORT",
            title=output.get("title") or request.get("title") or None,
            content=output.get("content") or "",
            status="PROPOSED",
            finding_refs=used_findings,
            fragment_refs=used_fragments,
            evidence_refs=sorted(evidence_refs),
            edit_kind="SEMANTIC",
            owner_step_task_id=run.step_task_id,
            source_skill_run_id=run.id,
            source_narrative_plan_id=plan.id,
            created_by=None,
        )
        await db.flush()
