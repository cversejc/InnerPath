from sqlalchemy import select

from app.application.skill_runtime import authorize_report_case
from app.core.time import api_datetime, utc_now_naive
from app.domains.content.models import CaseEvidenceItem, ContentFragmentRevision, FindingRevision, NarrativePlan
from app.domains.review.contracts import fingerprint, program_issues, approval_blockers, checkpoint_fingerprint, required_checkpoint_keys, group_review_issues
from app.domains.review.models import NodeReviewState, NodeReviewCommand, NodeApproval, NodeCheckpointApproval, POLICY_VERSION
from app.domains.workflow.authorization import validate_step_actor
from app.domains.workflow.models import ReportCase, StepTask


async def review_context(db, case_id, step_key, actor=None, *, write=False):
    case = await authorize_report_case(db, case_id, actor, allow_waiting=not write) if actor else await db.get(ReportCase, case_id)
    if not case or step_key not in {"S1", "S2", "S3", "S4", "S5", "S6"}:
        raise ValueError("report_case_not_found")
    if write:
        case = await db.scalar(select(ReportCase).where(ReportCase.id == case_id).with_for_update())
    step = await db.scalar(select(StepTask).where(StepTask.workflow_instance_id == case.workflow_instance_id, StepTask.step_key == step_key))
    if not step:
        raise ValueError("step_task_not_found")
    if write:
        validate_step_actor(step, actor)
        if case.status != "ACTIVE" or step.status != "IN_REVIEW":
            raise ValueError("step_not_in_review")
        current = await db.scalar(select(StepTask).where(StepTask.workflow_instance_id == case.workflow_instance_id, StepTask.status.in_(["READY", "IN_REVIEW", "EXECUTING", "WAITING_REVIEW"])).order_by(StepTask.sequence_no).limit(1))
        if not current or current.id != step.id:
            raise ValueError("report_analysis_step_not_current")
    if case.review_policy_version != POLICY_VERSION:
        raise ValueError("node_review_policy_migration_required")
    state = await db.scalar(select(NodeReviewState).where(NodeReviewState.report_case_id == case_id, NodeReviewState.step_key == step_key))
    return case, step, state


async def node_snapshot(db, case, step, state=None):
    allowed_steps = set(await db.scalars(select(StepTask.id).where(StepTask.workflow_instance_id == case.workflow_instance_id, StepTask.sequence_no <= step.sequence_no)))
    findings = list(await db.scalars(select(FindingRevision).where(FindingRevision.report_case_id == case.id, FindingRevision.is_current.is_(True), FindingRevision.status.not_in(["REJECTED", "SUPERSEDED"])).order_by(FindingRevision.finding_key)))
    fragments = list(await db.scalars(select(ContentFragmentRevision).where(ContentFragmentRevision.report_case_id == case.id, ContentFragmentRevision.is_current.is_(True)).order_by(ContentFragmentRevision.fragment_key)))
    findings = [f for f in findings if f.owner_step_task_id is None or f.owner_step_task_id in allowed_steps]
    fragments = [f for f in fragments if f.owner_step_task_id is None or f.owner_step_task_id in allowed_steps]
    evidence = list(await db.scalars(select(CaseEvidenceItem).where(CaseEvidenceItem.report_case_id == case.id, CaseEvidenceItem.status == "ACTIVE").order_by(CaseEvidenceItem.evidence_key)))
    selected = [f for f in fragments if (f.fragment_type == "REPORT" if step.step_key in {"S5", "S6"} else f.owner_step_task_id == step.id and f.fragment_type == "ANALYSIS")]
    fragment_data = lambda f: {"fragment_key": f.fragment_key, "id": f.id, "title": f.title, "content": f.content, "revision_no": f.revision_no, "semantic_revision": f.semantic_revision, "source_snapshot": f.source_snapshot, "status": "STALE" if f.status == "STALE" else "DRAFT", "owner_step_task_id": f.owner_step_task_id}
    plan = await db.scalar(select(NarrativePlan).where(NarrativePlan.report_case_id == case.id, NarrativePlan.is_current.is_(True)))
    narrative_confirmation = None
    report_generation = None
    if plan and step.step_key == "S5":
        narrative_confirmation = {"status": plan.status, "confirmed_by": plan.confirmed_by, "confirmed_at": api_datetime(plan.confirmed_at)}
        from app.application.report_generation import current_report_coherence_context
        coherence_context = await current_report_coherence_context(db, case.id)
        generation = (plan.plan_json or {}).get("generation") or {}
        coherence = (coherence_context or {}).get("coherence") or {}
        report_generation = {
            "status": generation.get("status"),
            "coherence": {
                "status": coherence.get("status"),
                "fingerprint": coherence.get("fingerprint"),
                "skill_run_id": coherence.get("skill_run_id"),
            },
        }
    snapshot = {"policy_version": case.review_policy_version, "step_key": step.step_key, "step_task_id": step.id, "activation_no": step.activation_no,
                "metadata": (state.metadata_json if state else {}) or {}, "fragments": [fragment_data(f) for f in selected],
                "source_fragments": [fragment_data(f) for f in fragments if f not in selected and f.fragment_type == "ANALYSIS"],
                "findings": [{"finding_key": f.finding_key, "id": f.id, "claim": f.claim, "revision_no": f.revision_no, "semantic_revision": f.semantic_revision, "semantic_role": f.semantic_role, "kind": f.kind, "confidence": f.confidence, "importance": f.importance, "reportability": f.reportability, "structured_data": f.structured_data_json, "evidence_refs": f.evidence_refs, "relation_refs": f.relation_refs, "owner_step_task_id": f.owner_step_task_id} for f in findings],
                "evidence": [{"evidence_key": e.evidence_key, "id": e.id, "value": e.value_json, "source_type": e.source_type} for e in evidence],
                "application_profile": (case.application_snapshot or {}).get("profile") or {},
                "narrative_plan": {**{k: v for k, v in (plan.plan_json or {}).items() if k != "generation"}, "status": plan.status} if plan and step.step_key in {"S5", "S6"} else None,
                "narrative_plan_confirmation": narrative_confirmation,
                "report_generation": report_generation,
                "framework_contract": (case.application_snapshot or {}).get("framework_contract"), "reasoning_contract": (case.application_snapshot or {}).get("reasoning_contract")}
    return snapshot


async def require_fingerprint(db, case, step, state, expected):
    snapshot = await node_snapshot(db, case, step, state)
    if not expected or fingerprint(snapshot) != expected:
        raise ValueError("node_review_version_conflict")
    return snapshot


async def review_workspace(db, case_id, step_key, actor):
    case, step, state = await review_context(db, case_id, step_key, actor)
    snapshot = await node_snapshot(db, case, step, state)
    version = fingerprint(snapshot)
    commands = list(await db.scalars(select(NodeReviewCommand).where(NodeReviewCommand.report_case_id == case_id, NodeReviewCommand.step_task_id == step.id).order_by(NodeReviewCommand.id.desc())))
    check = next((c for c in commands if c.kind == "CHECK" and c.fingerprint == version and c.activation_no == step.activation_no), None)
    # 已完成节点回看：优先展示本节点最后一次有效检查结果，避免用当前快照的程序检查替代历史结论。
    historical_check = None
    if check is None and step.status == "COMPLETED":
        historical_check = next((c for c in commands if c.kind == "CHECK" and c.status == "COMPLETED" and c.activation_no == step.activation_no), None)
    visible_check = check or historical_check
    issues = (visible_check.output_json or {}).get("issues", []) if visible_check and visible_check.status == "COMPLETED" else program_issues(snapshot)
    final_ready = True
    final_quality = None
    if step_key == "S6":
        from app.application.report_quality import quality_state
        final_quality = await quality_state(db, case)
        final_ready = final_quality.can_approve
        issues = [{"id": f"qa:{i.id}", "severity": i.severity, "status": i.status if i.status == "OPEN" else "RETAINED" if i.status == "ACCEPTED" else "FALSE_POSITIVE" if i.status == "DISMISSED" else "RESOLVED", "target_key": i.target_fragment_key, "message": i.message, "type": i.issue_type, "quote": (i.evidence_json or {}).get("evidence", ""), "source": i.source_type, "resolution": i.resolution} for i in final_quality.issues]
    approvals = list(await db.scalars(select(NodeApproval).where(NodeApproval.report_case_id == case_id, NodeApproval.step_task_id == step.id).order_by(NodeApproval.id.desc())))
    checkpoint_states = await checkpoint_state_map(
        db,
        case,
        step,
        snapshot,
        final_quality.model_dump(mode="json") if final_quality else None,
    )
    can_write = False
    try:
        validate_step_actor(step, actor)
        can_write = step.status == "IN_REVIEW" and case.status == "ACTIVE"
    except ValueError:
        pass
    birth_time_proposal = None
    if step_key == "S1":
        from app.domains.reports.generation.birth_time import resolve_birth_time
        try:
            birth_time_proposal = resolve_birth_time((case.application_snapshot or {}).get("profile") or {}, snapshot["metadata"].get("birth_time_confirmation"))
        except (ValueError, KeyError, TypeError):
            birth_time_proposal = {"status": "NEEDS_CONFIRMATION", "limitations": ["出生资料缺失，请补问后再核对"]}
    checkpoints_complete = all(item["current"] for item in checkpoint_states.values())
    return {"step_key": step_key, "step_status": step.status, "fingerprint": version, "snapshot": snapshot, "can_write": can_write,
            "issues": issues, "issue_groups": group_review_issues(issues), "check": command_data(visible_check) if visible_check else None,
            "check_historical": historical_check is not None, "birth_time_proposal": birth_time_proposal, "preparation_error": step.last_error,
            "checkpoints": checkpoint_states,
            "required_checkpoints": list(required_checkpoint_keys(step_key)),
            "can_approve": can_write and checkpoints_complete and (final_ready if step_key == "S6" else bool(check and check.status == "COMPLETED")) and not approval_blockers(issues) and final_ready,
            "final_quality": final_quality.model_dump(mode="json") if final_quality else None,
            "commands": [command_data(c) for c in commands[:15]],
            "approvals": [{"id": a.id, "fingerprint": a.fingerprint, "approved_by": a.approved_by, "approved_at": api_datetime(a.approved_at), "current": a.fingerprint == version and a.activation_no == step.activation_no} for a in approvals]}


async def checkpoint_state_map(db, case, step, snapshot, final_quality=None):
    records = list(await db.scalars(select(NodeCheckpointApproval).where(
        NodeCheckpointApproval.report_case_id == case.id,
        NodeCheckpointApproval.step_task_id == step.id,
    ).order_by(NodeCheckpointApproval.id.desc())))
    states = {}
    for key in required_checkpoint_keys(step.step_key):
        expected = checkpoint_fingerprint(snapshot, key, final_quality=final_quality)
        record = next((item for item in records
                       if item.checkpoint_key == key
                       and item.activation_no == step.activation_no
                       and item.policy_version == POLICY_VERSION
                       and item.fingerprint == expected), None)
        latest = next((item for item in records
                       if item.checkpoint_key == key
                       and item.activation_no == step.activation_no), None)
        states[key] = {
            "current": record is not None,
            "fingerprint": expected,
            "approved_by": record.approved_by if record else None,
            "approved_at": api_datetime(record.approved_at) if record else None,
            "stale": latest is not None and record is None,
        }
    return states


def command_data(command):
    return {"id": command.id, "kind": command.kind, "status": command.status, "fingerprint": command.fingerprint, "output": command.output_json, "error": command.error, "created_at": api_datetime(command.created_at), "completed_at": api_datetime(command.completed_at)} if command else None


async def save_metadata(db, case_id, step_key, value):
    state = await db.scalar(select(NodeReviewState).where(NodeReviewState.report_case_id == case_id, NodeReviewState.step_key == step_key))
    if state is None:
        state = NodeReviewState(report_case_id=case_id, step_key=step_key, metadata_json={}, updated_at=utc_now_naive())
        db.add(state)
    state.metadata_json = {**(state.metadata_json or {}), **value}
    state.updated_at = utc_now_naive()
    await db.flush()
    return state
