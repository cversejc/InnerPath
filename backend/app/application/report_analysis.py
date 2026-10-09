from app.domains.workflow.authorization import validate_step_actor
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
from app.domains.content.evidence import create_evidence_item, retract_case_evidence
from app.domains.reports.generation.mingli_foundation import (
    calculate_mingli_foundation,
)
from app.domains.skills.definitions import ANALYSIS_STEPS
from app.domains.skills.analysis_sop import display_topic_title, stage_contract
from app.domains.skills.models import SkillRun
from app.domains.skills.bindings import resolve_case_skill
from app.domains.workflow.models import StepTask
from app.domains.content.framework_coverage import analysis_coverage_issues
from app.domains.content.reasoning_contract import (
    ANALYSIS_STRUCTURES, normalize_structured_analysis, reasoning_issues, validate_timeline_source,
)
from app.domains.review.contracts import fingerprint
from app.models.user import User


ACTIVE_STEP_STATUSES = {"READY", "IN_REVIEW", "EXECUTING", "WAITING_REVIEW"}


def build_analysis_completion_gate(
    *, finding_statuses: list[str], fragment_statuses: list[str],
    required_topics: list[dict] | None = None, confirmed_fragment_keys: list[str] | None = None,
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
    missing_topics = [item for item in required_topics or [] if item["fragment_key"] not in (confirmed_fragment_keys or [])]
    if missing_topics:
        blockers.append("report_analysis_sop_coverage_required")
    return {
        "can_complete": not blockers,
        "confirmed_finding_count": confirmed_finding_count,
        "confirmed_fragment_count": confirmed_fragment_count,
        "pending_finding_count": pending_finding_count,
        "pending_fragment_count": pending_fragment_count,
        "stale_fragment_count": stale_fragment_count,
        "blockers": blockers,
        "missing_topics": missing_topics,
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
    validate_step_actor(step, actor)
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
    finding_rows, fragment_rows = list(finding_rows), list(fragment_rows)
    contract = stage_contract(step_key)
    framework = (report_case.application_snapshot or {}).get("framework_contract")
    coverage_issues = analysis_coverage_issues(framework, [
        {"fragment_key": row.fragment_key, "content": row.content, "source_snapshot": row.source_snapshot}
        for row in fragment_rows if row.status == "CONFIRMED"], stage=step_key) if framework else []
    gate = build_analysis_completion_gate(
        finding_statuses=[row.status for row in finding_rows],
        fragment_statuses=[row.status for row in fragment_rows],
        required_topics=contract["topics"] if contract else [],
        confirmed_fragment_keys=[row.fragment_key for row in fragment_rows if row.status == "CONFIRMED"],
    )
    if coverage_issues:
        gate["can_complete"] = False
        gate["blockers"].append("report_analysis_framework_coverage_required")
    reasoning_contract = (report_case.application_snapshot or {}).get("reasoning_contract")
    chain_issues = []
    if reasoning_contract:
        confirmed_findings = list(await db.scalars(select(FindingRevision).where(
            FindingRevision.report_case_id == case_id, FindingRevision.is_current.is_(True),
            FindingRevision.status == "CONFIRMED")))
        evidence = list(await db.scalars(select(CaseEvidenceItem).where(
            CaseEvidenceItem.report_case_id == case_id, CaseEvidenceItem.status == "ACTIVE")))
        chain_issues = reasoning_issues({"reasoning_contract": reasoning_contract,
            "findings": [{"finding_key": f.finding_key, "semantic_role": f.semantic_role,
                          "structured_data": f.structured_data_json} for f in confirmed_findings],
            "evidence": [{"evidence_key": e.evidence_key, "source_type": e.source_type, "value": e.value_json} for e in evidence],
            "analysis_fragments": [{"fragment_key": f.fragment_key, "content": f.content,
                                    "source_snapshot": f.source_snapshot} for f in fragment_rows if f.status == "CONFIRMED"]}, stage=step_key)
        if chain_issues:
            gate["can_complete"] = False
            gate["blockers"].append("report_analysis_reasoning_required")
    return {
        "step_key": step_key,
        "sop_contract": contract,
        "framework_coverage_issues": coverage_issues,
        "reasoning_issues": chain_issues,
        **gate,
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


def _is_mingli_foundation_evidence(item: CaseEvidenceItem) -> bool:
    if item.source_type not in {"SYSTEM_CALCULATED", "CONSULTANT_CORRECTED"}:
        return False
    key = item.evidence_key
    value = item.value_json
    return bool(
        key.startswith((
            "calculated.mingli_foundation.",
            "calculated.foundation.skill_run.",
        ))
        or key in {"system.bazi", "system.four_pillars", "system.ziwei"}
        or (
            isinstance(value, dict)
            and value.get("calculation_method") == "deterministic-mingli"
            and isinstance(value.get("bazi"), dict)
        )
    )


def _is_supported_mingli_v2(item: CaseEvidenceItem) -> bool:
    value = item.value_json
    return bool(
        _is_mingli_foundation_evidence(item)
        and isinstance(value, dict)
        and isinstance(value.get("bazi"), dict)
        and (
            item.source_type == "CONSULTANT_CORRECTED"
            and item.evidence_key.startswith("calculated.mingli_foundation.consultant.")
            and value.get("calculation_version") == "mingli-v2"
            or item.source_type == "SYSTEM_CALCULATED"
            and item.evidence_key.startswith("calculated.mingli_foundation.v2")
            and value.get("calculation_version") == "mingli-v2"
        )
    )


def _current_mingli_foundation(rows: list[CaseEvidenceItem]) -> CaseEvidenceItem | None:
    candidates = [item for item in rows if item.status == "ACTIVE" and _is_supported_mingli_v2(item)]
    corrections = [
        item for item in candidates
        if item.source_type == "CONSULTANT_CORRECTED"
        and item.evidence_key.startswith("calculated.mingli_foundation.consultant.")
    ]
    canonical = [
        item for item in candidates
        if item.source_type == "SYSTEM_CALCULATED"
        and item.evidence_key.startswith("calculated.mingli_foundation.v2")
    ]
    systems = [item for item in candidates if item.source_type == "SYSTEM_CALCULATED"]
    return max(corrections or canonical or systems, key=lambda item: (item.created_at, item.id), default=None)


async def _ensure_mingli_foundation(
    db: AsyncSession, *, report_case: Any
) -> CaseEvidenceItem:
    evidence_rows = list(await db.scalars(
        select(CaseEvidenceItem)
        .where(CaseEvidenceItem.report_case_id == report_case.id)
        .order_by(CaseEvidenceItem.created_at, CaseEvidenceItem.id)
    ))
    current = _current_mingli_foundation(evidence_rows)
    if current is not None:
        return current

    profile, _context = _stage_snapshot(report_case)
    if report_case.review_policy_version == "six-node-review-v1":
        from app.domains.review.models import NodeReviewState
        state = await db.scalar(select(NodeReviewState).where(NodeReviewState.report_case_id == report_case.id, NodeReviewState.step_key == "S1"))
        profile = {**profile, "review_time_policy": True, "birth_time_confirmation": (state.metadata_json or {}).get("birth_time_confirmation") if state else None}
    try:
        foundation = calculate_mingli_foundation(profile)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("report_analysis_foundation_required") from error

    base_key = "calculated.mingli_foundation.v2"
    existing_keys = {item.evidence_key for item in evidence_rows}
    evidence_key = base_key
    revision = 2
    while evidence_key in existing_keys:
        evidence_key = f"{base_key}.r{revision}"
        revision += 1
    return await create_evidence_item(
        db,
        report_case_id=report_case.id,
        evidence_key=evidence_key,
        source_type="SYSTEM_CALCULATED",
        source_ref="tool:reports.calculate_mingli_foundation:v2",
        value=foundation,
    )


async def get_or_calculate_report_case_foundation(
    db: AsyncSession, *, case_id: int, actor: User, step_key: str = "S1"
) -> CaseEvidenceItem:
    if step_key != "S1":
        raise ValueError("report_foundation_step_invalid")
    report_case, _step = await _authorize_analysis_step(
        db, case_id=case_id, step_key=step_key, actor=actor
    )
    return await _ensure_mingli_foundation(db, report_case=report_case)


async def correct_report_case_foundation(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    expected_evidence_key: str,
    value: dict[str, Any],
    reason: str,
    actor: User,
) -> CaseEvidenceItem:
    if step_key != "S1":
        raise ValueError("report_foundation_step_invalid")
    report_case, _step = await _authorize_analysis_step(
        db, case_id=case_id, step_key=step_key, actor=actor
    )
    if not isinstance(value, dict) or not isinstance(value.get("bazi"), dict):
        raise ValueError("report_foundation_value_invalid")
    if value.get("calculation_version") != "mingli-v2":
        raise ValueError("report_foundation_version_invalid")
    correction_reason = reason.strip()
    if len(correction_reason) < 3:
        raise ValueError("report_foundation_correction_reason_required")

    evidence_rows = list(await db.scalars(
        select(CaseEvidenceItem)
        .where(CaseEvidenceItem.report_case_id == report_case.id)
        .order_by(CaseEvidenceItem.created_at, CaseEvidenceItem.id)
    ))
    current = _current_mingli_foundation(evidence_rows)
    if current is None:
        current = await _ensure_mingli_foundation(db, report_case=report_case)
        evidence_rows.append(current)
    if current.evidence_key != expected_evidence_key:
        raise ValueError("report_foundation_revision_conflict")

    correction_no = 1 + sum(
        item.source_type == "CONSULTANT_CORRECTED"
        and item.evidence_key.startswith("calculated.mingli_foundation.consultant.")
        for item in evidence_rows
    )
    evidence_key = f"calculated.mingli_foundation.consultant.{correction_no}"
    corrected_value = deepcopy(value)
    corrected_value.pop("_consultant_correction", None)
    corrected_value["_consultant_correction"] = {
        "reason": correction_reason,
        "supersedes_evidence_key": current.evidence_key,
        "revision": correction_no,
    }

    foundation_evidence_keys = {
        item.evidence_key
        for item in evidence_rows
        if _is_mingli_foundation_evidence(item)
    }
    retired_evidence_keys = {
        item.evidence_key
        for item in evidence_rows
        if item.status == "ACTIVE" and item.evidence_key in foundation_evidence_keys
    }
    remaining_evidence_keys = {
        item.evidence_key
        for item in evidence_rows
        if item.status == "ACTIVE" and item.evidence_key not in foundation_evidence_keys
    }
    for item in evidence_rows:
        if item.status == "ACTIVE" and _is_mingli_foundation_evidence(item):
            await retract_case_evidence(
                db,
                report_case_id=report_case.id,
                evidence_key=item.evidence_key,
                reason=f"superseded_by_consultant_correction:{evidence_key}",
            )

    corrected_evidence = await create_evidence_item(
        db,
        report_case_id=report_case.id,
        evidence_key=evidence_key,
        source_type="CONSULTANT_CORRECTED",
        source_ref=f"consultant:foundation_correction:{current.evidence_key}",
        value=corrected_value,
        created_by=actor.id,
    )

    current_findings = list(await db.scalars(
        select(FindingRevision).where(
            FindingRevision.report_case_id == report_case.id,
            FindingRevision.is_current.is_(True),
            FindingRevision.status.in_(("PROPOSED", "CONFIRMED")),
        )
    ))
    affected_finding_keys = {
        finding.finding_key
        for finding in current_findings
        if any(key in foundation_evidence_keys for key in (finding.evidence_refs or []))
    }
    while True:
        newly_affected = {
            finding.finding_key
            for finding in current_findings
            if finding.finding_key not in affected_finding_keys
            and any(
                (relation.get("finding_key") if isinstance(relation, dict) else relation)
                in affected_finding_keys
                for relation in (finding.relation_refs or [])
            )
        }
        if not newly_affected:
            break
        affected_finding_keys.update(newly_affected)

    reviewable_finding_statuses = {
        finding.finding_key: finding.status for finding in current_findings
    }
    for finding in current_findings:
        if finding.finding_key not in affected_finding_keys:
            continue
        has_retired_reference = any(
            key in foundation_evidence_keys for key in (finding.evidence_refs or [])
        )
        if not has_retired_reference and finding.status == "PROPOSED":
            continue
        active_refs = [
            key for key in (finding.evidence_refs or [])
            if key in remaining_evidence_keys
        ]
        active_relations = [
            relation for relation in (finding.relation_refs or [])
            if (
                relation.get("finding_key") if isinstance(relation, dict) else relation
            ) in reviewable_finding_statuses
        ]
        structured_data = deepcopy(finding.structured_data_json or {})
        if (
            (report_case.application_snapshot or {}).get("reasoning_contract")
            and finding.semantic_role.upper() == "ACTION"
            and isinstance(structured_data, dict)
        ):
            structured_data["block_refs"] = [
                key for key in structured_data.get("block_refs", [])
                if key in reviewable_finding_statuses
            ]
            reasoning_path = structured_data.get("reasoning_path")
            if isinstance(reasoning_path, dict):
                reasoning_path["resource_refs"] = [
                    key for key in reasoning_path.get("resource_refs", [])
                    if key in reviewable_finding_statuses
                ]
        await create_finding_revision(
            db,
            report_case_id=report_case.id,
            finding_key=finding.finding_key,
            claim=finding.claim,
            kind=finding.kind,
            semantic_role=finding.semantic_role,
            confidence=finding.confidence,
            importance=finding.importance,
            reportability=finding.reportability,
            status="PROPOSED",
            evidence_refs=active_refs,
            relation_refs=active_relations,
            structured_data=structured_data,
            edit_kind="SEMANTIC",
            owner_step_task_id=finding.owner_step_task_id,
            source_skill_run_id=finding.source_skill_run_id,
            created_by=actor.id,
        )
    return corrected_evidence


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
    foundation_evidence = _current_mingli_foundation(evidence_rows)
    if step.step_key == "S1":
        foundation_evidence = await _ensure_mingli_foundation(
            db, report_case=report_case
        )
        if not any(item.id == foundation_evidence.id for item in evidence_rows):
            evidence_rows.append(foundation_evidence)
    evidence_rows = [
        item for item in evidence_rows
        if not _is_mingli_foundation_evidence(item)
        or (foundation_evidence is not None and item.id == foundation_evidence.id)
    ]
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
    foundation = (
        foundation_evidence.value_json
        if step.step_key == "S1" and foundation_evidence
        else None
    )

    analysis_context = {
        "report_case_id": report_case.id,
        "step_key": step.step_key,
        "activation_no": step.activation_no,
        "sop_contract": stage_contract(step.step_key),
        "framework_contract": (report_case.application_snapshot or {}).get("framework_contract"),
        "reasoning_contract": (report_case.application_snapshot or {}).get("reasoning_contract"),
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
                "relation_refs": item.relation_refs or [],
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
    source_run_id: int | None = None,
) -> tuple[SkillRun, bool]:
    report_case, step = await _authorize_analysis_step(
        db, case_id=case_id, step_key=step_key, actor=actor
    )
    if step_key == "S1" and report_case.review_policy_version == "six-node-review-v1":
        from app.application.node_review_workspace import checkpoint_state_map, node_snapshot
        from app.domains.review.models import NodeReviewState

        review_state = await db.scalar(
            select(NodeReviewState).where(
                NodeReviewState.report_case_id == report_case.id,
                NodeReviewState.step_key == "S1",
            )
        )
        confirmation = (review_state.metadata_json or {}).get("birth_time_confirmation") if review_state else None
        snapshot = await node_snapshot(db, report_case, step, review_state)
        checkpoints = await checkpoint_state_map(db, report_case, step, snapshot)
        if not (confirmation or {}).get("confirmed") or not checkpoints.get("birth_data", {}).get("current"):
            raise ValueError("birth_time_confirmation_required")
    if step_key == "S1":
        active_foundation_rows = list(await db.scalars(
            select(CaseEvidenceItem).where(
                CaseEvidenceItem.report_case_id == report_case.id,
                CaseEvidenceItem.status == "ACTIVE",
            )
        ))
        if _current_mingli_foundation(active_foundation_rows) is None:
            raise ValueError("report_analysis_foundation_required")
    stage = ANALYSIS_STEPS[step_key]
    skill = await resolve_case_skill(db, report_case, stage["skill_key"])
    if report_case.review_policy_version == "six-node-review-v1":
        from app.application.node_review_workspace import node_snapshot

        current_snapshot = snapshot if step_key == "S1" else await node_snapshot(db, report_case, step)
        current_fingerprint = fingerprint(current_snapshot)
        pending_run = await db.scalar(
            select(SkillRun)
            .where(
                SkillRun.report_case_id == report_case.id,
                SkillRun.step_task_id == step.id,
                SkillRun.skill_version_id == skill.id,
                SkillRun.target_type == "REPORT_ANALYSIS_DRAFT",
                SkillRun.target_key == step_key,
                SkillRun.status.in_(["PENDING", "RUNNING"]),
            )
            .order_by(SkillRun.id.desc())
            .limit(1)
        )
        if (
            pending_run is not None
            and (pending_run.context_snapshot or {}).get("analysis_activation_no") == step.activation_no
            and (pending_run.context_snapshot or {}).get("node_input_fingerprint") == current_fingerprint
        ):
            return pending_run, False
    analysis_context, foundation = await _analysis_context(
        db, report_case=report_case, step=step
    )
    if source_run_id is not None:
        previous_run = await db.scalar(
            select(SkillRun).where(SkillRun.id == source_run_id)
        )
        if (
            previous_run is None
            or previous_run.report_case_id != report_case.id
            or previous_run.step_task_id != step.id
            or previous_run.skill_version_id != skill.id
            or previous_run.target_type != "REPORT_ANALYSIS_DRAFT"
            or previous_run.target_key != step_key
            or previous_run.status != "COMPLETED"
            or not isinstance(previous_run.output_parsed, dict)
            or (previous_run.context_snapshot or {}).get("analysis_activation_no")
            != step.activation_no
        ):
            raise ValueError("report_analysis_feedback_source_invalid")
        analysis_context["previous_analysis"] = {
            "source_run_id": previous_run.id,
            "output_parsed": deepcopy(previous_run.output_parsed),
        }
        if step_key == "S1":
            previous_foundation = next(
                (
                    item.get("evidence_key")
                    for item in ((previous_run.input_snapshot or {}).get("analysis_context") or {}).get("evidence", [])
                    if isinstance(item, dict)
                    and item.get("source_type") in {"SYSTEM_CALCULATED", "CONSULTANT_CORRECTED"}
                    and str(item.get("evidence_key", "")).startswith((
                        "calculated.mingli_foundation.v2",
                        "calculated.mingli_foundation.consultant.",
                    ))
                    and isinstance(item.get("value"), dict)
                    and item["value"].get("calculation_version") == "mingli-v2"
                ),
                None,
            )
            current_foundation = next(
                (
                    item.get("evidence_key")
                    for item in analysis_context.get("evidence", [])
                    if isinstance(item, dict)
                    and item.get("source_type") in {"SYSTEM_CALCULATED", "CONSULTANT_CORRECTED"}
                    and str(item.get("evidence_key", "")).startswith((
                        "calculated.mingli_foundation.v2",
                        "calculated.mingli_foundation.consultant.",
                    ))
                    and isinstance(item.get("value"), dict)
                    and item["value"].get("calculation_version") == "mingli-v2"
                ),
                None,
            )
            if previous_foundation and previous_foundation != current_foundation:
                raise ValueError("report_analysis_feedback_source_stale")
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
            "analysis_feedback_source_run_id": source_run_id,
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
    run_analysis_context = (run.input_snapshot or {}).get("analysis_context") or {}
    run_foundation = next(
        (
            item for item in run_analysis_context.get("evidence", [])
            if isinstance(item, dict)
            and item.get("source_type") in {"SYSTEM_CALCULATED", "CONSULTANT_CORRECTED"}
            and str(item.get("evidence_key", "")).startswith((
                "calculated.mingli_foundation.v2",
                "calculated.mingli_foundation.consultant.",
            ))
            and isinstance(item.get("value"), dict)
            and item["value"].get("calculation_version") == "mingli-v2"
        ),
        None,
    )
    if run_foundation is not None:
        active_evidence = list(await db.scalars(
            select(CaseEvidenceItem).where(
                CaseEvidenceItem.report_case_id == report_case.id,
                CaseEvidenceItem.status == "ACTIVE",
            )
        ))
        current_foundation = _current_mingli_foundation(active_evidence)
        if (
            current_foundation is None
            or current_foundation.evidence_key != run_foundation.get("evidence_key")
        ):
            raise ValueError("report_analysis_candidate_evidence_stale")
    return run


async def _require_active_candidate_evidence(
    db: AsyncSession, *, report_case_id: int, candidate: dict[str, Any]
) -> None:
    for evidence_key in candidate.get("evidence_refs") or []:
        row = await db.scalar(
            select(CaseEvidenceItem).where(
                CaseEvidenceItem.report_case_id == report_case_id,
                CaseEvidenceItem.evidence_key == evidence_key,
            )
        )
        if row is None or row.status != "ACTIVE":
            raise ValueError("report_analysis_candidate_evidence_stale")


async def apply_analysis_finding_candidate(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    run_id: int,
    finding_key: str,
    expected_revision_no: int | None,
    actor: User,
    review: dict[str, Any] | None = None,
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
    await _require_active_candidate_evidence(
        db, report_case_id=case_id, candidate=candidate
    )
    current = await current_finding(db, case_id, finding_key)
    if (current.revision_no if current else None) != expected_revision_no:
        raise ValueError("finding_revision_conflict")
    if current and current.owner_step_task_id not in (None, step.id):
        raise ValueError("report_analysis_candidate_owned_by_another_step")
    if current and current.source_skill_run_id == run.id and review is None:
        return current
    candidate = {**candidate, **{
        key: value for key, value in (review or {}).items()
        if key in {"claim", "kind", "semantic_role", "confidence", "importance", "reportability",
                   "evidence_refs", "relation_refs", "structured_data"}
    }}
    if review is not None and not candidate.get("evidence_refs") and not candidate.get("relation_refs"):
        raise ValueError("report_analysis_finding_support_required")
    structured_data = deepcopy(candidate.get("structured_data") or {})
    short_title = candidate.get("short_title")
    if isinstance(short_title, str) and short_title.strip():
        structured_data["short_title"] = short_title.strip()
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
        status=(review or {}).get("status", "PROPOSED"),
        evidence_refs=candidate.get("evidence_refs") or [],
        relation_refs=candidate.get("relation_refs") or [],
        structured_data=structured_data,
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
    review: dict[str, Any] | None = None,
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
    await _require_active_candidate_evidence(
        db, report_case_id=case_id, candidate=candidate
    )
    candidate = {**candidate, **{
        key: value for key, value in (review or {}).items()
        if key in {"title", "content", "finding_refs", "evidence_refs", "framework_coverage", "structured_analysis"}
    }}
    if review is not None and not candidate.get("finding_refs") and not candidate.get("evidence_refs"):
        raise ValueError("report_analysis_fragment_support_required")
    for referenced_key in candidate.get("finding_refs") or []:
        referenced_finding = await current_finding(db, case_id, referenced_key)
        if referenced_finding is None or not (referenced_finding.status == "CONFIRMED" or (report_case.review_policy_version == "six-node-review-v1" and referenced_finding.status == "PROPOSED" and referenced_finding.owner_step_task_id == step.id)):
            raise ValueError("report_analysis_fragment_findings_unconfirmed")
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
    if current and current.source_skill_run_id == run.id and review is None:
        return current
    if fragment_key == "analysis.s3.timeline" and candidate.get("structured_analysis") is not None:
        record = normalize_structured_analysis(fragment_key, candidate["structured_analysis"], candidate["content"])
        evidence_rows = list(await db.scalars(select(CaseEvidenceItem).where(
            CaseEvidenceItem.report_case_id == case_id, CaseEvidenceItem.status == "ACTIVE",
        )))
        validate_timeline_source(record, [
            {"evidence_key": row.evidence_key, "source_type": row.source_type, "value": row.value_json}
            for row in evidence_rows
        ], set(candidate.get("evidence_refs") or []))
    title = display_topic_title(candidate.get("title"))
    return await create_content_fragment_revision(
        db,
        report_case_id=case_id,
        fragment_key=fragment_key,
        fragment_type="ANALYSIS",
        title=title,
        content=candidate["content"],
        framework_coverage=candidate.get("framework_coverage"),
        structured_analysis=(
            candidate.get("structured_analysis")
            if fragment_key in ANALYSIS_STRUCTURES
            else None
        ),
        status=(review or {}).get("status", "PROPOSED"),
        finding_refs=candidate.get("finding_refs") or [],
        fragment_refs=[],
        evidence_refs=candidate.get("evidence_refs") or [],
        edit_kind="SEMANTIC",
        owner_step_task_id=step.id,
        source_skill_run_id=run.id,
        created_by=actor.id,
    )



def relation_targets(candidate: dict[str, Any]) -> set[str]:
    """Candidate finding keys referenced by one candidate's relation_refs."""
    targets = set()
    for ref in candidate.get("relation_refs") or []:
        if isinstance(ref, str):
            targets.add(ref)
        elif isinstance(ref, dict) and isinstance(ref.get("finding_key"), str):
            targets.add(ref["finding_key"])
    return targets


async def apply_analysis_run_candidates(
    db: AsyncSession,
    *,
    case_id: int,
    step_key: str,
    run_id: int,
    actor: User,
) -> dict[str, Any]:
    """Add one completed analysis run to the node as proposed content."""
    report_case, step = await _authorize_analysis_step(
        db, case_id=case_id, step_key=step_key, actor=actor
    )
    run = await _analysis_run_for_apply(
        db, report_case=report_case, step=step, run_id=run_id
    )
    output = run.output_parsed or {}
    finding_candidates = output.get("findings") or []
    fragment_candidates = output.get("analysis_fragments") or []
    if not finding_candidates and not fragment_candidates:
        raise ValueError("report_analysis_candidates_empty")

    pending_findings = {}
    for candidate in finding_candidates:
        key = candidate.get("finding_key") if isinstance(candidate, dict) else None
        if not isinstance(key, str) or not key or key in pending_findings:
            raise ValueError("report_analysis_candidate_invalid")
        pending_findings[key] = candidate

    applied_findings = []
    existing_findings = []
    cycle_breaks: list[dict[str, Any]] = []
    while pending_findings:
        for key in list(pending_findings):
            current = await current_finding(db, case_id, key)
            if current and current.source_skill_run_id == run.id:
                existing_findings.append(key)
                del pending_findings[key]
        if not pending_findings:
            break

        ready = []
        for key, candidate in pending_findings.items():
            refs = candidate.get("relation_refs") or []
            dependencies = set()
            for ref in refs:
                if isinstance(ref, str):
                    dependencies.add(ref)
                elif isinstance(ref, dict):
                    dependencies.add(ref.get("finding_key"))
                else:
                    raise ValueError("finding_relation_invalid")
            if not dependencies.intersection(pending_findings):
                ready.append((key, candidate))
        if not ready:
            # 候选之间互相引用（例如互为对立面）时不存在能满足全部引用的应用顺序。
            # 按最少待定依赖优先断环，只剪掉指向尚未写入候选的引用，避免整批失败。
            ordered = list(pending_findings)
            key = min(
                ordered,
                key=lambda item: (
                    len(relation_targets(pending_findings[item]).intersection(ordered)),
                    ordered.index(item),
                ),
            )
            candidate = pending_findings[key]
            kept, pruned = [], []
            for ref in candidate.get("relation_refs") or []:
                target = ref if isinstance(ref, str) else ref.get("finding_key") if isinstance(ref, dict) else None
                if target in pending_findings:
                    pruned.append(target)
                else:
                    kept.append(ref)
            if pruned:
                candidate["relation_refs"] = kept
                cycle_breaks.append({"finding_key": key, "pruned_relation_keys": pruned, "pruned_relation_count": len(pruned)})
            ready.append((key, candidate))

        for key, candidate in ready:
            current = await current_finding(db, case_id, key)
            await apply_analysis_finding_candidate(
                db,
                case_id=case_id,
                step_key=step_key,
                run_id=run_id,
                finding_key=key,
                expected_revision_no=current.revision_no if current else None,
                actor=actor,
            )
            applied_findings.append(key)
            del pending_findings[key]

    pending_fragments = {}
    for candidate in fragment_candidates:
        key = candidate.get("fragment_key") if isinstance(candidate, dict) else None
        if not isinstance(key, str) or not key or key in pending_fragments:
            raise ValueError("report_analysis_candidate_invalid")
        pending_fragments[key] = candidate

    applied_fragments = []
    existing_fragments = []
    for key in pending_fragments:
        current = await db.scalar(
            select(ContentFragmentRevision)
            .where(
                ContentFragmentRevision.report_case_id == case_id,
                ContentFragmentRevision.fragment_key == key,
                ContentFragmentRevision.is_current.is_(True),
            )
            .with_for_update()
        )
        if current and current.source_skill_run_id == run.id:
            existing_fragments.append(key)
            continue
        await apply_analysis_fragment_candidate(
            db,
            case_id=case_id,
            step_key=step_key,
            run_id=run_id,
            fragment_key=key,
            expected_revision_no=current.revision_no if current else None,
            actor=actor,
        )
        applied_fragments.append(key)

    if cycle_breaks:
        # 断环后的候选引用已在内存中收敛，回写一次保证与本次应用结果一致。
        run.output_parsed = output
    return {
        "cycle_breaks": cycle_breaks,
        "pruned_relation_count": sum(item["pruned_relation_count"] for item in cycle_breaks),
        "finding_count": len(applied_findings),
        "fragment_count": len(applied_fragments),
        "existing_finding_count": len(existing_findings),
        "existing_fragment_count": len(existing_fragments),
        "finding_keys": applied_findings + existing_findings,
        "fragment_keys": applied_fragments + existing_fragments,
    }
