from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.skill_runtime import authorize_report_case, _queue_run
from app.domains.content.findings import create_finding_revision, current_finding
from app.domains.content.fragments import create_content_fragment_revision
from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
)
from app.domains.reports.generation.mingli_foundation import (
    calculate_mingli_foundation,
)
from app.domains.skills.definitions import ANALYSIS_STEPS
from app.domains.skills.models import SkillRun
from app.domains.skills.service import ensure_default_analysis_skill_versions
from app.domains.workflow.models import StepTask
from app.models.user import User


ACTIVE_STEP_STATUSES = {"READY", "IN_REVIEW", "EXECUTING", "WAITING_REVIEW"}


def build_analysis_completion_gate(
    *, finding_statuses: list[str], fragment_statuses: list[str]
) -> dict[str, Any]:
    confirmed_finding_count = finding_statuses.count("CONFIRMED")
    confirmed_fragment_count = fragment_statuses.count("CONFIRMED")
    pending_finding_count = finding_statuses.count("PROPOSED")
    pending_fragment_count = fragment_statuses.count("PROPOSED")
    stale_fragment_count = fragment_statuses.count("STALE")
    blockers = []
    if pending_finding_count:
        blockers.append("report_analysis_findings_unreviewed")
    if pending_fragment_count:
        blockers.append("report_analysis_fragments_unreviewed")
    if stale_fragment_count:
        blockers.append("report_analysis_fragments_stale")
    if confirmed_finding_count + confirmed_fragment_count == 0:
        blockers.append("report_analysis_output_required")
    return {
        "can_complete": not blockers,
        "confirmed_finding_count": confirmed_finding_count,
        "confirmed_fragment_count": confirmed_fragment_count,
        "pending_finding_count": pending_finding_count,
        "pending_fragment_count": pending_fragment_count,
        "stale_fragment_count": stale_fragment_count,
        "blockers": blockers,
    }


async def _authorize_analysis_step(
    db: AsyncSession, *, case_id: int, step_key: str, actor: User
) -> tuple[Any, StepTask]:
    if step_key not in ANALYSIS_STEPS:
        raise ValueError("report_analysis_step_invalid")
    report_case = await authorize_report_case(db, case_id, actor)
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
    if actor.role == "consultant" and step.assignee_id not in (None, actor.id):
        raise ValueError("step_assigned_to_another_consultant")
    current = await db.scalar(
        select(StepTask)
        .where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.status.in_(ACTIVE_STEP_STATUSES),
        )
        .order_by(StepTask.sequence_no)
        .limit(1)
    )
    if current is None or current.id != step.id:
        raise ValueError("report_analysis_step_not_current")
    if step.status != "IN_REVIEW":
        raise ValueError("report_analysis_step_not_in_review")
    return report_case, step


async def get_analysis_step_completion_gate(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    actor: User,
) -> dict[str, Any]:
    report_case, step = await _authorize_analysis_step(
        db, case_id=case_id, step_key=step_key, actor=actor
    )
    finding_rows = await db.scalars(
        select(FindingRevision).where(
            FindingRevision.report_case_id == report_case.id,
            FindingRevision.owner_step_task_id == step.id,
            FindingRevision.is_current.is_(True),
        )
    )
    fragment_rows = await db.scalars(
        select(ContentFragmentRevision).where(
            ContentFragmentRevision.report_case_id == report_case.id,
            ContentFragmentRevision.owner_step_task_id == step.id,
            ContentFragmentRevision.fragment_type == "ANALYSIS",
            ContentFragmentRevision.is_current.is_(True),
        )
    )
    return {
        "step_key": step_key,
        **build_analysis_completion_gate(
            finding_statuses=[row.status for row in finding_rows],
            fragment_statuses=[row.status for row in fragment_rows],
        ),
    }


async def validate_analysis_step_completion(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    actor: User,
) -> None:
    gate = await get_analysis_step_completion_gate(
        db, case_id=case_id, step_key=step_key, actor=actor
    )
    if gate["blockers"]:
        raise ValueError(gate["blockers"][0])


def _stage_snapshot(report_case: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = deepcopy(report_case.application_snapshot or {})
    source = snapshot.get("request_payload")
    if not isinstance(source, dict):
        source = snapshot
    profile = source.get("profile") or source.get("user_profile") or {}
    context = source.get("context") or {}
    context = dict(context) if isinstance(context, dict) else {}
    if source.get("selected_topics") and "focus_topics" not in context:
        context["focus_topics"] = source["selected_topics"]
    if source.get("additional_info") and "additional_info" not in context:
        context["additional_info"] = source["additional_info"]
    return dict(profile) if isinstance(profile, dict) else {}, context


async def _analysis_context(
    db: AsyncSession, *, report_case: Any, step: StepTask
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    task_rows = await db.scalars(
        select(StepTask)
        .where(StepTask.workflow_instance_id == report_case.workflow_instance_id)
        .order_by(StepTask.sequence_no)
    )
    tasks = list(task_rows)
    previous_task_ids = {
        item.id for item in tasks if item.sequence_no < step.sequence_no
    }

    evidence_rows = list(await db.scalars(
        select(CaseEvidenceItem)
        .where(
            CaseEvidenceItem.report_case_id == report_case.id,
            CaseEvidenceItem.status == "ACTIVE",
        )
        .order_by(CaseEvidenceItem.evidence_key)
    ))
    evidence = [
        {
            "evidence_key": item.evidence_key,
            "source_type": item.source_type,
            "source_ref": item.source_ref,
            "value": item.value_json,
        }
        for item in evidence_rows
    ]

    finding_rows = await db.scalars(
        select(FindingRevision)
        .where(
            FindingRevision.report_case_id == report_case.id,
            FindingRevision.is_current.is_(True),
        )
        .order_by(FindingRevision.finding_key)
    )
    findings = list(finding_rows)
    upstream_findings = [
        item
        for item in findings
        if item.status == "CONFIRMED" and item.owner_step_task_id in previous_task_ids
    ]

    fragment_rows = await db.scalars(
        select(ContentFragmentRevision)
        .where(
            ContentFragmentRevision.report_case_id == report_case.id,
            ContentFragmentRevision.is_current.is_(True),
            ContentFragmentRevision.fragment_type == "ANALYSIS",
        )
        .order_by(ContentFragmentRevision.fragment_key)
    )
    fragments = list(fragment_rows)
    upstream_fragments = [
        item
        for item in fragments
        if item.status == "CONFIRMED" and item.owner_step_task_id in previous_task_ids
    ]

    profile, application_context = _stage_snapshot(report_case)
    foundation = None
    if step.step_key == "S1":
        foundation_evidence = next(
            (
                item
                for item in evidence_rows
                if item.source_type == "SYSTEM_CALCULATED"
                and isinstance(item.value_json, dict)
                and item.value_json.get("calculation_method") == "deterministic-mingli"
            ),
            None,
        )
        if foundation_evidence is None:
            try:
                foundation = calculate_mingli_foundation(profile)
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("report_analysis_foundation_required") from error
            from app.domains.content.evidence import create_evidence_item

            foundation_evidence = await create_evidence_item(
                db,
                report_case_id=report_case.id,
                evidence_key="calculated.mingli_foundation.v1",
                source_type="SYSTEM_CALCULATED",
                source_ref="tool:reports.calculate_mingli_foundation:v1",
                value=foundation,
            )
            evidence.append(
                {
                    "evidence_key": foundation_evidence.evidence_key,
                    "source_type": foundation_evidence.source_type,
                    "source_ref": foundation_evidence.source_ref,
                    "value": foundation_evidence.value_json,
                }
            )
        else:
            foundation = foundation_evidence.value_json

    analysis_context = {
        "report_case_id": report_case.id,
        "step_key": step.step_key,
        "activation_no": step.activation_no,
        "application_snapshot": report_case.application_snapshot or {},
        "evidence": evidence,
        "upstream_confirmed_findings": [
            {
                "finding_key": item.finding_key,
                "claim": item.claim,
                "semantic_role": item.semantic_role,
                "confidence": item.confidence,
                "importance": item.importance,
                "evidence_refs": item.evidence_refs or [],
                "structured_data": item.structured_data_json or {},
            }
            for item in upstream_findings
        ],
        "upstream_confirmed_analysis_fragments": [
            {
                "fragment_key": item.fragment_key,
                "title": item.title,
                "content": item.content,
                "source_snapshot": item.source_snapshot or {},
            }
            for item in upstream_fragments
        ],
        "current_stage_findings": [
            {
                "finding_key": item.finding_key,
                "status": item.status,
                "claim": item.claim,
                "revision_no": item.revision_no,
                "semantic_role": item.semantic_role,
            }
            for item in findings
            if item.owner_step_task_id == step.id
        ],
        "current_stage_analysis_fragments": [
            {
                "fragment_key": item.fragment_key,
                "status": item.status,
                "title": item.title,
                "content": item.content,
                "revision_no": item.revision_no,
            }
            for item in fragments
            if item.owner_step_task_id == step.id
        ],
    }
    return analysis_context, foundation


async def queue_case_analysis_draft(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    actor: User,
    idempotency_key: str,
    runtime_instruction: str | None = None,
) -> tuple[SkillRun, bool]:
    report_case, step = await _authorize_analysis_step(
        db, case_id=case_id, step_key=step_key, actor=actor
    )
    versions = await ensure_default_analysis_skill_versions(db)
    stage = ANALYSIS_STEPS[step_key]
    skill = next(item for item in versions if item.skill_key == stage["skill_key"])
    analysis_context, foundation = await _analysis_context(
        db, report_case=report_case, step=step
    )
    profile, application_context = _stage_snapshot(report_case)
    input_data: dict[str, Any] = {
        "profile": profile,
        "context": application_context,
        "analysis_context": analysis_context,
    }
    if foundation is not None:
        input_data["foundation_data"] = foundation
    return await _queue_run(
        db,
        version_id=skill.id,
        idempotency_key=idempotency_key,
        input_data=input_data,
        runtime_instruction=runtime_instruction,
        target_type="REPORT_ANALYSIS_DRAFT",
        target_key=step_key,
        report_case=report_case,
        step=step,
        context_metadata={
            "analysis_step_key": step_key,
            "analysis_activation_no": step.activation_no,
        },
    )


async def _analysis_run_for_apply(
    db: AsyncSession,
    *,
    report_case: Any,
    step: StepTask,
    run_id: int,
) -> SkillRun:
    run = await db.scalar(
        select(SkillRun).where(SkillRun.id == run_id).with_for_update()
    )
    if (
        run is None
        or run.report_case_id != report_case.id
        or run.workflow_instance_id != report_case.workflow_instance_id
        or run.step_task_id != step.id
        or run.target_type != "REPORT_ANALYSIS_DRAFT"
        or run.target_key != step.step_key
    ):
        raise ValueError("report_analysis_run_not_found")
    if run.status != "COMPLETED":
        raise ValueError("report_analysis_run_not_completed")
    if (run.context_snapshot or {}).get("analysis_activation_no") != step.activation_no:
        raise ValueError("report_analysis_run_activation_changed")
    return run


async def apply_analysis_finding_candidate(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    run_id: int,
    finding_key: str,
    expected_revision_no: int | None,
    actor: User,
) -> FindingRevision:
    report_case, step = await _authorize_analysis_step(
        db, case_id=case_id, step_key=step_key, actor=actor
    )
    run = await _analysis_run_for_apply(
        db, report_case=report_case, step=step, run_id=run_id
    )
    candidate = next(
        (
            item
            for item in (run.output_parsed or {}).get("findings", [])
            if item.get("finding_key") == finding_key
        ),
        None,
    )
    if candidate is None:
        raise ValueError("report_analysis_candidate_not_found")
    current = await current_finding(db, case_id, finding_key)
    if (current.revision_no if current else None) != expected_revision_no:
        raise ValueError("finding_revision_conflict")
    if current and current.owner_step_task_id not in (None, step.id):
        raise ValueError("report_analysis_candidate_owned_by_another_step")
    if current and current.source_skill_run_id == run.id:
        return current
    return await create_finding_revision(
        db,
        report_case_id=case_id,
        finding_key=finding_key,
        claim=candidate["claim"],
        kind=candidate["kind"],
        semantic_role=candidate["semantic_role"],
        confidence=candidate["confidence"],
        importance=candidate["importance"],
        reportability=candidate["reportability"],
        status="PROPOSED",
        evidence_refs=candidate.get("evidence_refs") or [],
        relation_refs=candidate.get("relation_refs") or [],
        structured_data=candidate.get("structured_data") or {},
        edit_kind="SEMANTIC",
        owner_step_task_id=step.id,
        source_skill_run_id=run.id,
        created_by=actor.id,
    )


async def apply_analysis_fragment_candidate(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    run_id: int,
    fragment_key: str,
    expected_revision_no: int | None,
    actor: User,
) -> ContentFragmentRevision:
    report_case, step = await _authorize_analysis_step(
        db, case_id=case_id, step_key=step_key, actor=actor
    )
    run = await _analysis_run_for_apply(
        db, report_case=report_case, step=step, run_id=run_id
    )
    candidate = next(
        (
            item
            for item in (run.output_parsed or {}).get("analysis_fragments", [])
            if item.get("fragment_key") == fragment_key
        ),
        None,
    )
    if candidate is None:
        raise ValueError("report_analysis_candidate_not_found")
    current = await db.scalar(
        select(ContentFragmentRevision)
        .where(
            ContentFragmentRevision.report_case_id == case_id,
            ContentFragmentRevision.fragment_key == fragment_key,
            ContentFragmentRevision.is_current.is_(True),
        )
        .with_for_update()
    )
    if (current.revision_no if current else None) != expected_revision_no:
        raise ValueError("fragment_revision_conflict")
    if current and current.owner_step_task_id not in (None, step.id):
        raise ValueError("report_analysis_candidate_owned_by_another_step")
    if current and current.source_skill_run_id == run.id:
        return current
    return await create_content_fragment_revision(
        db,
        report_case_id=case_id,
        fragment_key=fragment_key,
        fragment_type="ANALYSIS",
        title=candidate.get("title"),
        content=candidate["content"],
        status="PROPOSED",
        finding_refs=candidate.get("finding_refs") or [],
        fragment_refs=[],
        evidence_refs=candidate.get("evidence_refs") or [],
        edit_kind="SEMANTIC",
        owner_step_task_id=step.id,
        source_skill_run_id=run.id,
        created_by=actor.id,
    )
