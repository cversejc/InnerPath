"""Outbox continuations prepare work; only consultants can sign nodes."""
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.application.node_review_workspace import review_context, node_snapshot, save_metadata
from app.application.node_review_commands import queue_review_command
from app.domains.review.contracts import fingerprint
from app.domains.review.schemas import ReviewCommandInput
from app.domains.review.models import POLICY_VERSION, NodeReviewState, NodeReviewCommand
from app.domains.workflow.models import ReportCase, StepTask
from app.domains.workflow.authorization import validate_step_actor
from app.domains.workflow.service import start_step
from app.domains.content.models import ContentFragmentRevision, FindingRevision, NarrativePlan
from app.domains.skills.models import SkillRun
from app.models.user import User


async def prepare_node(db, case_id, step_id, activation_no, *, retry_key=None):
    case = await db.scalar(select(ReportCase).where(ReportCase.id == case_id).with_for_update())
    step = await db.get(StepTask, step_id)
    if not case or case.review_policy_version != POLICY_VERSION or case.status != "ACTIVE" or not step or step.workflow_instance_id != case.workflow_instance_id or step.activation_no != activation_no or step.status not in {"READY", "IN_REVIEW"}:
        return "stale"
    if not step.assignee_id:
        return "waiting_for_assignment"
    actor = await db.get(User, step.assignee_id)
    if not actor:
        return "waiting_for_assignment"
    try:
        validate_step_actor(step, actor)
    except ValueError:
        return "waiting_for_permission"
    if step.status == "READY":
        await start_step(db, case.id, step.step_key)
    await db.commit()
    _, _, state = await review_context(db, case.id, step.step_key)
    snapshot = await node_snapshot(db, case, step, state)
    key = f"node-prepare:{case.id}:{step.step_key}:{step.activation_no}:{retry_key or fingerprint(snapshot)[:24]}"
    try:
        if step.step_key in {"S1", "S2", "S3", "S4"}:
            from app.application.report_analysis import _ensure_mingli_foundation, queue_case_analysis_draft
            if step.step_key == "S1":
                await _ensure_mingli_foundation(db, report_case=case)
                await db.commit()
            # A reopened node preserves its complete draft; it needs a new check/signature.
            if snapshot["fragments"] and not retry_key:
                return await auto_check(db, case, step, actor)
            run, _ = await queue_case_analysis_draft(db, case_id=case.id, step_key=step.step_key, actor=actor, idempotency_key=key)
        elif step.step_key == "S5":
            from app.application.skill_runtime import queue_case_authoring_skill_run
            from app.application.report_generation import start_case_report_generation
            plan = await db.scalar(select(NarrativePlan).where(NarrativePlan.report_case_id == case.id, NarrativePlan.is_current.is_(True)))
            if plan and plan.status in {"PROPOSED", "CONFIRMED"}:
                if (plan.plan_json.get("generation") or {}).get("status") == "READY_FOR_REVIEW":
                    return await auto_check(db, case, step, actor)
                await start_case_report_generation(db, case_id=case.id, actor=actor, idempotency_key=key)
                return "generating"
            run, _ = await queue_case_authoring_skill_run(db, case_id=case.id, step_key="S5", actor=actor, skill_key="report.narrative_plan", idempotency_key=key)
            if run.status == "PENDING":
                run.runtime_instruction = "将最推荐的主线放在candidates第一项；先提供可直接据此生成全文的完整方案，人工将在全文生成后整体审阅主线和编排。"
                await db.commit()
        else:
            return await auto_check(db, case, step, actor)
        return run.status.lower()
    except ValueError as error:
        await db.rollback()
        step = await db.get(StepTask, step_id)
        step.last_error = str(error)
        await db.commit()
        return "needs_input"


async def auto_check(db, case, step, actor):
    _, _, state = await review_context(db, case.id, step.step_key)
    snapshot = await node_snapshot(db, case, step, state)
    version = fingerprint(snapshot)
    await queue_review_command(db, case.id, step.step_key, actor, ReviewCommandInput(fingerprint=version, idempotency_key=f"auto-check:{case.id}:{step.step_key}:{step.activation_no}:{version}"), "CHECK")
    return "checking"


async def continue_node_run(db, run):
    if not run.report_case_id:
        return
    case = await db.scalar(select(ReportCase).where(ReportCase.id == run.report_case_id).with_for_update())
    if case.review_policy_version != POLICY_VERSION:
        return
    step = await db.get(StepTask, run.step_task_id) if run.step_task_id else None
    if not step:
        return
    metadata = run.context_snapshot or {}
    if run.status == "FAILED":
        step.last_error = run.error
        if run.target_type == "REPORT_QA":
            from app.core.time import utc_now_naive
            checks = list(await db.scalars(select(NodeReviewCommand).where(NodeReviewCommand.report_case_id == case.id, NodeReviewCommand.step_task_id == step.id, NodeReviewCommand.kind == "CHECK", NodeReviewCommand.status == "RUNNING")))
            for check in checks:
                if (check.output_json or {}).get("validator_run_id") == run.id:
                    check.status, check.error, check.completed_at = "FAILED", run.error, utc_now_naive()
        await db.commit()
        return
    if run.status != "COMPLETED" or metadata.get("node_materialized") or metadata.get("node_archived"):
        return
    if run.target_type == "REPORT_QA":
        # A finished validator run supersedes stale errors and RUNNING CHECK rows even when the
        # node's current actor can no longer be resolved, so reconcile before the holder guards.
        from app.core.time import utc_now_naive
        checks = list(await db.scalars(select(NodeReviewCommand).where(NodeReviewCommand.report_case_id == case.id, NodeReviewCommand.step_task_id == step.id, NodeReviewCommand.kind == "CHECK", NodeReviewCommand.status == "RUNNING")))
        _, _, state = await review_context(db, case.id, step.step_key)
        current_version = fingerprint(await node_snapshot(db, case, step, state))
        for check in checks:
            if (check.output_json or {}).get("validator_run_id") == run.id:
                check.status = "COMPLETED" if check.fingerprint == current_version and check.activation_no == step.activation_no else "STALE"
                check.completed_at = utc_now_naive()
        step.last_error = None
        await db.commit()
        return
    actor = await db.get(User, step.assignee_id) if step.assignee_id else None
    if not actor or case.status in {"DELIVERED", "CANCELLED"} or step.status != "IN_REVIEW":
        return
    validate_step_actor(step, actor)
    if run.target_type in {"REPORT_ANALYSIS_DRAFT", "NARRATIVE_CANDIDATES"}:
        _, _, state = await review_context(db, case.id, step.step_key)
        if metadata.get("node_input_fingerprint") != fingerprint(await node_snapshot(db, case, step, state)) or metadata.get("node_review_policy") != POLICY_VERSION:
            run.context_snapshot = {**metadata, "node_archived": "input_version_changed"}
            await db.commit()
            return
        if run.target_type == "REPORT_ANALYSIS_DRAFT":
            from app.application.report_analysis import apply_analysis_finding_candidate, apply_analysis_fragment_candidate
            # Relations can point forward in a model's output. Materialize in dependency order.
            pending = list((run.output_parsed or {}).get("findings", []))
            while pending:
                progressed = False
                for candidate in list(pending):
                    refs = [r if isinstance(r, str) else r.get("finding_key") for r in candidate.get("relation_refs", [])]
                    known = set(await db.scalars(select(FindingRevision.finding_key).where(FindingRevision.report_case_id == case.id, FindingRevision.is_current.is_(True))))
                    if not set(refs).issubset(known):
                        continue
                    existing = await db.scalar(select(FindingRevision).where(FindingRevision.report_case_id == case.id, FindingRevision.finding_key == candidate["finding_key"], FindingRevision.is_current.is_(True)))
                    if not existing or (existing.status != "CONFIRMED" and existing.created_by is None):
                        row = await apply_analysis_finding_candidate(db, case_id=case.id, step_key=step.step_key, run_id=run.id, finding_key=candidate["finding_key"], expected_revision_no=existing.revision_no if existing else None, actor=actor)
                        row.created_by = None
                    pending.remove(candidate)
                    progressed = True
                if not progressed:
                    raise ValueError("node_generation_relation_cycle_or_missing")
            for candidate in (run.output_parsed or {}).get("analysis_fragments", []):
                existing = await db.scalar(select(ContentFragmentRevision).where(ContentFragmentRevision.report_case_id == case.id, ContentFragmentRevision.fragment_key == candidate["fragment_key"], ContentFragmentRevision.is_current.is_(True)))
                if existing and (existing.status == "CONFIRMED" or existing.created_by is not None):
                    continue
                row = await apply_analysis_fragment_candidate(db, case_id=case.id, step_key=step.step_key, run_id=run.id, fragment_key=candidate["fragment_key"], expected_revision_no=existing.revision_no if existing else None, actor=actor)
                row.created_by = None
        else:
            from app.domains.content.narrative import confirm_narrative_plan
            from app.application.report_generation import start_case_report_generation
            candidates = (run.output_parsed or {}).get("candidates") or []
            if not candidates:
                raise ValueError("narrative_candidate_not_found")
            plan = await confirm_narrative_plan(db, report_case_id=case.id, skill_run_id=run.id, candidate_key=candidates[0]["candidate_key"], overrides={}, actor_id=None, as_draft=True)
            run.context_snapshot = {**metadata, "node_materialized": True}
            await db.commit()
            await start_case_report_generation(db, case_id=case.id, actor=actor, idempotency_key=f"node-full-report:{case.id}:{plan.id}:{step.activation_no}")
            return
        run.context_snapshot = {**metadata, "node_materialized": True}
        step.last_error = None
        await db.commit()
        await auto_check(db, case, step, actor)
    elif run.target_type == "REPORT_COHERENCE":
        plan = await db.scalar(select(NarrativePlan).where(NarrativePlan.report_case_id == case.id, NarrativePlan.is_current.is_(True)))
        if plan and (plan.plan_json.get("generation") or {}).get("status") == "READY_FOR_REVIEW":
            await auto_check(db, case, step, actor)
