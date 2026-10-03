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
    ANALYSIS_STEPS,
    DEFAULT_SKILL_KEY,
    default_skill_specification,
)
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.examples import retrieve_skill_examples
from app.domains.skills.evaluation import evaluate_regression_output
from app.domains.skills.runtime import (
    DeepSeekGateway,
    ModelGateway,
    SkillExecutionError,
    build_context_envelope,
    execute_skill,
)
from app.domains.skills.service import (
    create_skill_run,
    ensure_default_analysis_skill_versions,
    ensure_default_skill_version,
    ensure_default_validator_skill_version,
)
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
from app.domains.workflow.service import (
    create_workflow_draft,
    latest_published_version,
    publish_workflow_version,
)
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


async def ensure_analysis_workflow_version(db: AsyncSession) -> WorkflowVersion:
    latest = await latest_published_version(db, DEFAULT_WORKFLOW_KEY)
    if latest is not None:
        steps = latest.definition_json.get("steps", [])
        by_key = {step.get("step_key"): step for step in steps}
        if all(
            by_key.get(step_key, {}).get("executor") == "HYBRID"
            and by_key.get(step_key, {}).get("config", {}).get("skill_key")
            == stage["skill_key"]
            for step_key, stage in ANALYSIS_STEPS.items()
        ):
            return latest

    skill_versions = await ensure_default_analysis_skill_versions(db)
    skill_by_key = {skill.skill_key: skill for skill in skill_versions}
    definition = default_workflow_definition()
    for step in definition["steps"]:
        stage = ANALYSIS_STEPS.get(step["step_key"])
        if stage is None:
            continue
        skill = skill_by_key[stage["skill_key"]]
        step["executor"] = "HYBRID"
        step["config"].update(
            {"skill_key": skill.skill_key, "skill_version_id": skill.id}
        )

    authoring = await ensure_default_skill_version(db)
    authoring_step = next(
        step for step in definition["steps"] if step["step_key"] == "S5"
    )
    authoring_step["executor"] = "HYBRID"
    authoring_step["config"].update(
        {"skill_key": DEFAULT_SKILL_KEY, "skill_version_id": authoring.id}
    )
    try:
        async with db.begin_nested():
            version = await create_workflow_draft(
                db,
                DEFAULT_WORKFLOW_KEY,
                "咨询师报告生产流程·AI分析",
                definition,
                created_by=None,
            )
            await publish_workflow_version(db, version.id, published_by=None)
        return version
    except IntegrityError:
        existing = await latest_published_version(db, DEFAULT_WORKFLOW_KEY)
        if existing is not None:
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


async def authorize_report_case(
    db: AsyncSession, case_id: int, actor: User
) -> ReportCase:
    return await _authorize_case(db, case_id, actor)


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
    context_metadata: dict[str, Any] | None = None,
    run_type: str | None = None,
    commit: bool = True,
) -> tuple[SkillRun, bool]:
    skill_version = await db.get(AISkillVersion, version_id)
    if skill_version is None:
        raise ValueError("skill_version_not_found")
    specification = skill_version.specification_json
    base_input = build_context_envelope(input_data, specification)
    example_policy = specification.get("example_policy") or {}
    selected_examples = []
    if example_policy.get("enabled"):
        max_examples = example_policy.get("max_examples", 0)
        if not isinstance(max_examples, int) or isinstance(max_examples, bool):
            max_examples = 0
        selected_examples = await retrieve_skill_examples(
            db,
            skill_key=skill_version.skill_key,
            target_key=target_key if target_type == "REPORT_FRAGMENT" else None,
            context=base_input.get("context") or {},
            max_examples=max_examples,
        )
    input_snapshot = build_context_envelope(
        {
            **input_data,
            "few_shot_examples": [
                item["example_snapshot"] for item in selected_examples
            ],
        },
        specification,
    )
    context_snapshot = deepcopy(input_snapshot)
    context_snapshot.update(context_metadata or {})
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
        run_type=run_type or ("EVALUATION" if report_case is None else "INITIAL"),
        target_type=target_type,
        target_key=target_key,
        report_case_id=report_case.id if report_case else None,
        workflow_instance_id=report_case.workflow_instance_id if report_case else None,
        step_task_id=step.id if step else None,
        runtime_instruction=runtime_instruction,
        selected_examples=selected_examples,
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
    if not commit:
        return run, created
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


def _project_semantic_model(
    semantic_model: dict[str, Any], allocation: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    finding_refs = set(allocation.get("finding_refs") or [])
    analysis_refs = set(allocation.get("analysis_refs") or [])
    evidence_refs = set(allocation.get("evidence_refs") or [])
    findings = [
        item
        for item in semantic_model.get("findings", [])
        if item.get("finding_key") in finding_refs
    ]
    analysis_fragments = [
        item
        for item in semantic_model.get("analysis_fragments", [])
        if item.get("fragment_key") in analysis_refs
    ]
    evidence_refs.update(
        evidence_key
        for finding in findings
        for evidence_key in finding.get("evidence_refs", [])
    )
    for fragment in analysis_fragments:
        evidence_refs.update(
            row.get("evidence_key")
            for row in (fragment.get("source_snapshot") or {}).get("evidence", [])
            if isinstance(row, dict) and row.get("evidence_key")
        )
    return {
        "findings": findings,
        "analysis_fragments": analysis_fragments,
        "evidence": [
            item
            for item in semantic_model.get("evidence", [])
            if item.get("evidence_key") in evidence_refs
        ],
    }


async def queue_allocated_fragment_skill_run(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    step: StepTask,
    plan: NarrativePlan,
    semantic_model: dict[str, Any],
    allocation: dict[str, Any],
    idempotency_key: str,
    runtime_instruction: str | None = None,
    continuity: dict[str, Any] | None = None,
    generation_metadata: dict[str, Any] | None = None,
    run_type: str = "INITIAL",
    commit: bool = True,
) -> tuple[SkillRun, bool]:
    fragment_key = allocation.get("fragment_key")
    if not isinstance(fragment_key, str) or not fragment_key:
        raise ValueError("report_fragment_allocation_invalid")
    skill_version = await db.scalar(
        select(AISkillVersion)
        .where(
            AISkillVersion.skill_key == "report.fragment_authoring",
            AISkillVersion.status == "PUBLISHED",
        )
        .order_by(AISkillVersion.version.desc())
        .limit(1)
    )
    if skill_version is None:
        raise ValueError("narrative_skill_unavailable")

    application_snapshot = _safe_input_snapshot(report_case.application_snapshot or {})
    context = dict(application_snapshot.get("context") or {})
    context.update(
        {
            "semantic_model": _project_semantic_model(semantic_model, allocation),
            "narrative_plan": {
                key: value
                for key, value in (plan.plan_json or {}).items()
                if key not in {"content_plan", "generation"}
            },
            "narrative_plan_id": plan.id,
            "fragment_request": {
                "fragment_key": fragment_key,
                "title": fragment_key.rsplit(".", 1)[-1].replace("_", " "),
            },
            "fragment_allocation": allocation,
            "continuity": continuity or {},
        }
    )
    input_data = {
        **application_snapshot,
        "context": context,
        "semantic_source_snapshot": semantic_source_snapshot(semantic_model),
        "source_narrative_plan_id": plan.id,
    }
    context_metadata = (
        {"report_generation": generation_metadata}
        if generation_metadata is not None
        else None
    )
    return await _queue_run(
        db,
        version_id=skill_version.id,
        idempotency_key=idempotency_key,
        input_data=input_data,
        runtime_instruction=runtime_instruction,
        target_type="REPORT_FRAGMENT",
        target_key=fragment_key,
        report_case=report_case,
        step=step,
        context_metadata=context_metadata,
        run_type=run_type,
        commit=commit,
    )


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


async def queue_regression_skill_run(
    db: AsyncSession,
    *,
    version_id: int,
    idempotency_key: str,
    input_data: dict[str, Any],
    context_metadata: dict[str, Any],
    case_key: str,
) -> tuple[SkillRun, bool]:
    return await _queue_run(
        db,
        version_id=version_id,
        idempotency_key=idempotency_key,
        input_data=input_data,
        runtime_instruction=None,
        target_type="REGRESSION",
        target_key=case_key,
        context_metadata=context_metadata,
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
        content_plan = (plan.plan_json or {}).get("content_plan")
        if isinstance(content_plan, dict):
            if content_plan.get("status") != "READY":
                raise ValueError("report_content_plan_blocked")
            allocation = next(
                (
                    item
                    for item in content_plan.get("fragments", [])
                    if isinstance(item, dict)
                    and item.get("fragment_key") == fragment_key.strip()
                ),
                None,
            )
            if allocation is None:
                raise ValueError("report_fragment_not_in_content_plan")
            if (plan.plan_json.get("generation") or {}).get("status") == "IN_PROGRESS":
                raise ValueError("report_generation_in_progress")
            return await queue_allocated_fragment_skill_run(
                db,
                report_case=report_case,
                step=step,
                plan=plan,
                semantic_model=semantic_model,
                allocation=allocation,
                idempotency_key=idempotency_key,
                runtime_instruction=runtime_instruction,
                continuity=(plan.plan_json.get("generation") or {}).get("continuity"),
                run_type="REGENERATE",
            )
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


async def queue_case_report_coherence_skill_run(
    db: AsyncSession,
    *,
    report_case: ReportCase,
    step: StepTask,
    plan: NarrativePlan,
    semantic_model: dict[str, Any],
    content_plan: dict[str, Any],
    fragment_snapshot: list[dict[str, Any]],
    coherence_fingerprint: str,
    idempotency_key: str,
    generation_metadata: dict[str, Any],
    scope: str = "REPORT",
    chapter_key: str | None = None,
) -> tuple[SkillRun, bool]:
    skill_version = await ensure_default_validator_skill_version(db)
    application_snapshot = report_case.application_snapshot or {}
    profile = application_snapshot.get("profile") or {}
    qa_input = {
        "application_context": {
            "context": application_snapshot.get("context") or {},
            "selected_topics": application_snapshot.get("selected_topics") or [],
        },
        "confirmed_semantics": semantic_model,
        "narrative_plan": {
            key: value
            for key, value in (plan.plan_json or {}).items()
            if key not in {"content_plan", "generation"}
        },
        "content_plan": content_plan,
        "validation_scope": (
            ["chapter_coherence"]
            if scope == "CHAPTER"
            else [
                "report_coherence",
                "repetition",
                "block_to_action_link",
                "source_fidelity",
            ]
        ),
        "report_fragments": fragment_snapshot,
    }
    if chapter_key:
        qa_input["chapter_key"] = chapter_key
    return await _queue_run(
        db,
        version_id=skill_version.id,
        idempotency_key=idempotency_key,
        input_data={
            "profile": {"name": profile.get("name")},
            "context": {"qa_input": qa_input},
            "semantic_source_snapshot": semantic_source_snapshot(semantic_model),
            "source_narrative_plan_id": plan.id,
        },
        runtime_instruction=None,
        target_type=(
            "REPORT_CHAPTER_COHERENCE" if scope == "CHAPTER" else "REPORT_COHERENCE"
        ),
        target_key=(f"chapter:{chapter_key}" if scope == "CHAPTER" else "report.coherence"),
        report_case=report_case,
        step=step,
        context_metadata={
            "report_generation": generation_metadata,
            "coherence_fingerprint": coherence_fingerprint,
        },
        run_type="VALIDATE",
        commit=False,
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
                "report_generation",
                "qa_fingerprint",
                "coherence_fingerprint",
                "evaluation",
                "analysis_step_key",
                "analysis_activation_no",
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
        if run.target_type == "REGRESSION":
            evaluation = deepcopy(run_metadata.get("evaluation") or {})
            evaluation["result"] = evaluate_regression_output(
                run.output_parsed or {}, evaluation.get("expectation") or {}
            )
            run_metadata["evaluation"] = evaluation
            run.context_snapshot = {
                **run.context_snapshot,
                "evaluation": evaluation,
            }
        run.model_trace = {
            **result.model_trace,
            "selected_examples": [
                {
                    "example_id": item.get("example_id"),
                    "version_no": item.get("version_no"),
                    "retrieval_score": item.get("retrieval_score"),
                    "retrieval_policy": item.get("retrieval_policy"),
                    "selection_reasons": item.get("selection_reasons"),
                }
                for item in (run.selected_examples or [])
            ],
        }
    except SkillExecutionError as error:
        run.status = "FAILED"
        run.error = str(error)
        run.model_trace = error.model_trace
    except Exception as error:
        run.status = "FAILED"
        run.error = (
            str(error) if isinstance(error, ValueError) else type(error).__name__
        )
    if run.target_type == "REGRESSION" and run.status == "FAILED":
        evaluation = deepcopy((run.context_snapshot or {}).get("evaluation") or {})
        evaluation["result"] = {
            "score": 0.0,
            "minimum_score": (evaluation.get("expectation") or {}).get(
                "minimum_score", 1.0
            ),
            "passed": False,
            "checks": [{"name": "skill_execution", "passed": False, "actual": run.error}],
        }
        run.context_snapshot = {**(run.context_snapshot or {}), "evaluation": evaluation}
        flag_modified(run, "context_snapshot")
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
    allocation = context.get("fragment_allocation")
    if isinstance(allocation, dict):
        if allocation.get("fragment_key") != (request.get("fragment_key") or run.target_key):
            raise ValueError("report_fragment_allocation_invalid")
        allocated_findings = set(allocation.get("finding_refs") or [])
        allocated_analysis = set(allocation.get("analysis_refs") or [])
        allocated_actions = set(allocation.get("action_refs") or [])
        used_actions = output.get("used_actions") or []
        if any(item not in allocated_findings for item in used_findings):
            raise ValueError("report_fragment_unallocated_finding")
        if any(item not in allocated_analysis for item in used_fragments):
            raise ValueError("report_fragment_unallocated_analysis")
        if any(item not in allocated_actions for item in used_actions):
            raise ValueError("report_fragment_unallocated_action")
        if allocated_actions and not (set(used_actions) & allocated_actions):
            raise ValueError("report_fragment_action_support_missing")
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
