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
from app.domains.content.narrative_lineage import (
    allocation_semantic_sources_match,
    narrative_semantic_sources_match,
    semantic_source_snapshot_for_allocation,
)
from app.domains.content.queries import load_case_semantic_model
from app.domains.skills.definitions import (
    ANALYSIS_STEPS,
    default_skill_specification,
)
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.bindings import resolve_case_skill
from app.domains.skills.lifecycle import require_active_skill
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
    ensure_default_narrative_skill_versions,
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
from app.domains.workflow.authorization import is_assigned, assignment_condition, validate_step_actor


async def ensure_skill_workflow_version(db: AsyncSession) -> WorkflowVersion:
    """Compatibility entry point; initialize only the current production flow."""
    return await ensure_analysis_workflow_version(db)


async def ensure_analysis_workflow_version(db: AsyncSession) -> WorkflowVersion:
    skill_versions = [
        *await ensure_default_analysis_skill_versions(db),
        *await ensure_default_narrative_skill_versions(db),
        await ensure_default_validator_skill_version(db),
    ]
    skill_by_key = {skill.skill_key: skill for skill in skill_versions}

    latest = await latest_published_version(db, DEFAULT_WORKFLOW_KEY)
    if latest is not None:
        steps = latest.definition_json.get("steps", [])
        by_key = {step.get("step_key"): step for step in steps}
        analysis_shape_matches = all(
            by_key.get(step_key, {}).get("executor") == "HYBRID"
            and by_key.get(step_key, {}).get("config", {}).get("skill_key")
            == stage["skill_key"]
            for step_key, stage in ANALYSIS_STEPS.items()
        )
        authoring_config = by_key.get("S5", {}).get("config", {})
        analysis_shape_matches = (
            analysis_shape_matches
            and by_key.get("S5", {}).get("executor") == "HYBRID"
            and authoring_config.get("skill_key") in {None, "report.generate"}
        )
        uses_current_authoring = (
            authoring_config.get("authoring_mode") == "NARRATIVE_FRAGMENTS"
            and "skill_key" not in authoring_config
            and "skill_version_id" not in authoring_config
        )
        frozen_bindings = latest.definition_json.get("skill_bindings") or {}
        bindings_match = set(frozen_bindings) == set(skill_by_key) and all(
            (
                entry.get("id") if isinstance(entry, dict) else entry
            )
            == skill.id
            for skill_key, skill in skill_by_key.items()
            for entry in [frozen_bindings.get(skill_key)]
        )
        step_versions_match = all(
            by_key.get(step_key, {}).get("config", {}).get("skill_version_id")
            == skill_by_key[stage["skill_key"]].id
            for step_key, stage in ANALYSIS_STEPS.items()
        ) and uses_current_authoring
        if analysis_shape_matches and bindings_match and step_versions_match:
            return latest
        if (
            analysis_shape_matches
            and uses_current_authoring
            and "report.generate" not in frozen_bindings
            and (latest.created_by is not None or latest.published_by is not None)
        ):
            # An administrator may intentionally pin a reviewed workflow to
            # specific skill versions. Only refresh system-owned workflows.
            return latest

    # Keep the current published workflow's operational settings (including
    # collaboration policy) while rebinding it to the latest published skills.
    # Historical workflow versions and cases remain frozen as-is.
    definition = (
        deepcopy(latest.definition_json)
        if latest is not None and analysis_shape_matches
        else default_workflow_definition()
    )
    for step in definition["steps"]:
        stage = ANALYSIS_STEPS.get(step["step_key"])
        if stage is None:
            continue
        skill = skill_by_key[stage["skill_key"]]
        step["executor"] = "HYBRID"
        step["config"].update(
            {"skill_key": skill.skill_key, "skill_version_id": skill.id}
        )

    authoring_step = next(
        step for step in definition["steps"] if step["step_key"] == "S5"
    )
    authoring_step["executor"] = "HYBRID"
    authoring_step["config"].pop("skill_key", None)
    authoring_step["config"].pop("skill_version_id", None)
    authoring_step["config"]["authoring_mode"] = "NARRATIVE_FRAGMENTS"
    # Let workflow publication freeze a fresh snapshot of all seven report
    # skills; the previous frozen map belongs to the historical version.
    definition.pop("skill_bindings", None)
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
    if report_case.service_request_id is not None:
        request_status = await db.scalar(
            select(ServiceRequest.status).where(
                ServiceRequest.id == report_case.service_request_id
            )
        )
        if request_status == "needs_info":
            raise ValueError("report_case_waiting_for_user_info")
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
        or not is_assigned(request_row, actor.id)
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
    require_active_skill(skill_version.skill_key)
    if skill_version.status == "RETIRED":
        raise ValueError("skill_retired")
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
    feedback_rerun = (input_data.get("context") or {}).get("feedback_rerun")
    if isinstance(feedback_rerun, dict):
        input_snapshot.setdefault("context", {})["feedback_rerun"] = deepcopy(
            feedback_rerun
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
        run.selected_knowledge = deepcopy(specification.get("knowledge_policy", {}).get("snapshot") or [])
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
    if semantic_model.get("reasoning_contract"):
        for finding in findings:
            path = (finding.get("structured_data") or {}).get("reasoning_path") or {}
            if isinstance(path, dict):
                evidence_refs.update(path.get("evidence_refs") or [])
    for fragment in analysis_fragments:
        evidence_refs.update(
            row.get("evidence_key")
            for row in (fragment.get("source_snapshot") or {}).get("evidence", [])
            if isinstance(row, dict) and row.get("evidence_key")
        )
    return {
        "findings": findings,
        "analysis_fragments": analysis_fragments,
        **({"framework_reference": {k: semantic_model["framework_contract"][k] for k in ("version", "digest", "policies")}} if semantic_model.get("framework_contract") else {}),
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
    feedback_source_run: SkillRun | None = None,
    continuity: dict[str, Any] | None = None,
    generation_metadata: dict[str, Any] | None = None,
    run_type: str = "INITIAL",
    commit: bool = True,
) -> tuple[SkillRun, bool]:
    fragment_key = allocation.get("fragment_key")
    if not isinstance(fragment_key, str) or not fragment_key:
        raise ValueError("report_fragment_allocation_invalid")
    skill_version = await resolve_case_skill(db, report_case, "report.fragment_authoring")

    application_snapshot = _safe_input_snapshot(report_case.application_snapshot or {})
    context = dict(application_snapshot.get("context") or {})
    context.update(
        {
            "semantic_model": _project_semantic_model(semantic_model, allocation),
            "narrative_plan": {
                key: value
                for key, value in (plan.plan_json or {}).items()
                if key not in {"content_plan", "generation", "framework_contract"}
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
    if feedback_source_run is not None:
        context["feedback_rerun"] = {
            "source_run_id": feedback_source_run.id,
            "previous_ai_output": deepcopy(feedback_source_run.output_parsed),
        }
    input_data = {
        **application_snapshot,
        "context": context,
        "semantic_source_snapshot": semantic_source_snapshot_for_allocation(
            allocation, semantic_model
        ),
        "source_narrative_plan_id": plan.id,
    }
    context_metadata = {}
    if generation_metadata is not None:
        context_metadata["report_generation"] = generation_metadata
    context_metadata["authoring_step_key"] = step.step_key
    context_metadata["authoring_activation_no"] = step.activation_no
    if feedback_source_run is not None:
        context_metadata["authoring_feedback_source_run_id"] = feedback_source_run.id
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
        context_metadata=context_metadata or None,
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
    if step_key == "S5":
        raise ValueError("report_authoring_workflow_required")
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
    validate_step_actor(step, actor)
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


async def _authoring_feedback_source_run(
    db: AsyncSession,
    *,
    source_run_id: int | None,
    report_case: ReportCase,
    step: StepTask,
    skill_version_id: int,
    target_type: str,
    target_key: str,
) -> SkillRun | None:
    if source_run_id is None:
        return None
    source = await db.scalar(select(SkillRun).where(SkillRun.id == source_run_id))
    source_context = (source.context_snapshot or {}) if source is not None else {}
    source_activation = source_context.get("authoring_activation_no")
    if (
        source is None
        or source.report_case_id != report_case.id
        or source.workflow_instance_id != report_case.workflow_instance_id
        or source.step_task_id != step.id
        or source.skill_version_id != skill_version_id
        or source.target_type != target_type
        or source.target_key != target_key
        or source.status != "COMPLETED"
        or not isinstance(source.output_parsed, dict)
        or (
            source_activation is not None
            and source_activation != step.activation_no
        )
    ):
        raise ValueError("authoring_feedback_source_invalid")
    return source


async def queue_case_authoring_skill_run(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    actor: User,
    skill_key: str,
    idempotency_key: str,
    runtime_instruction: str | None = None,
    source_run_id: int | None = None,
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
    validate_step_actor(step, actor)
    if skill_key not in {"report.narrative_plan", "report.fragment_authoring"}:
        raise ValueError("narrative_skill_unavailable")

    skill_version = await resolve_case_skill(db, report_case, skill_key)
    feedback = (runtime_instruction or "").strip()
    if feedback and source_run_id is None:
        raise ValueError("authoring_feedback_source_required")

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
        previous_run = await _authoring_feedback_source_run(
            db,
            source_run_id=source_run_id,
            report_case=report_case,
            step=step,
            skill_version_id=skill_version.id,
            target_type=target_type,
            target_key=target_key,
        )
        if previous_run is not None:
            context["feedback_rerun"] = {
                "source_run_id": previous_run.id,
                "previous_ai_output": deepcopy(previous_run.output_parsed),
            }
            input_data["context"] = context
    else:
        plan = await get_current_narrative_plan(db, case_id)
        if plan is None or plan.status != "CONFIRMED":
            raise ValueError("narrative_plan_confirmation_required")
        if not narrative_semantic_sources_match(plan, semantic_model):
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
            previous_run = await _authoring_feedback_source_run(
                db,
                source_run_id=source_run_id,
                report_case=report_case,
                step=step,
                skill_version_id=skill_version.id,
                target_type="REPORT_FRAGMENT",
                target_key=fragment_key.strip(),
            )
            return await queue_allocated_fragment_skill_run(
                db,
                report_case=report_case,
                step=step,
                plan=plan,
                semantic_model=semantic_model,
                allocation=allocation,
                idempotency_key=idempotency_key,
                runtime_instruction=feedback or None,
                feedback_source_run=previous_run,
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
        previous_run = await _authoring_feedback_source_run(
            db,
            source_run_id=source_run_id,
            report_case=report_case,
            step=step,
            skill_version_id=skill_version.id,
            target_type=target_type,
            target_key=target_key,
        )
        if previous_run is not None:
            context["feedback_rerun"] = {
                "source_run_id": previous_run.id,
                "previous_ai_output": deepcopy(previous_run.output_parsed),
            }
            input_data["context"] = context

    return await _queue_run(
        db,
        version_id=skill_version.id,
        idempotency_key=idempotency_key,
        input_data=input_data,
        runtime_instruction=feedback or None,
        target_type=target_type,
        target_key=target_key,
        report_case=report_case,
        step=step,
        run_type="REGENERATE" if source_run_id is not None else "INITIAL",
        context_metadata={
            "authoring_step_key": step.step_key,
            "authoring_activation_no": step.activation_no,
            **(
                {"authoring_feedback_source_run_id": source_run_id}
                if source_run_id is not None
                else {}
            ),
        },
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
    if skill_version.skill_key == "report.generate" or skill_version.status == "RETIRED":
        run.status = "FAILED"
        run.error = "skill_retired"
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
                "analysis_feedback_source_run_id",
                "authoring_step_key",
                "authoring_activation_no",
                "authoring_feedback_source_run_id",
                "quality_feedback_source_run_id",
                "quality_activation_no",
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
    allocation = context.get("fragment_allocation")
    saved_source_snapshot = (run.context_snapshot or {}).get(
        "semantic_source_snapshot"
    ) or {}
    if isinstance(allocation, dict):
        if not allocation_semantic_sources_match(
            saved_source_snapshot, allocation, semantic_now
        ):
            raise ValueError("narrative_semantics_changed")
    elif semantic_source_snapshot(semantic_now) != saved_source_snapshot:
        raise ValueError("narrative_semantics_changed")
    if not narrative_semantic_sources_match(plan, semantic_now):
        raise ValueError("narrative_semantics_changed")

    used_findings = output.get("used_findings") or []
    used_fragments = output.get("used_analysis_fragments") or []
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
        if allocation.get("requirements") and (
            not allocated_analysis.issubset(used_fragments) or not allocated_actions.issubset(used_actions)
            or not set(allocation.get("required_finding_refs") or []).issubset(used_findings)
        ):
            raise ValueError("framework_allocated_source_uncovered")
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
            requirement_coverage=output.get("requirement_coverage"),
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
