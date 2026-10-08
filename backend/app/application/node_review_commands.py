import json
from copy import deepcopy

from sqlalchemy import select
from app.core.time import utc_now_naive
from app.application.node_review_workspace import review_context, require_fingerprint, node_snapshot, save_metadata, checkpoint_state_map
from app.domains.review.contracts import CHECK_PROMPT, REVISION_PROMPT, fingerprint, program_issues, source_texts, normalize_ai_issues, approval_blockers, checkpoint_fingerprint, checkpoint_scope, required_checkpoint_keys
from app.domains.review.models import NodeReviewState, NodeReviewCommand, NodeApproval, NodeCheckpointApproval, POLICY_VERSION
from app.domains.review.drafts import edit_draft, edit_narrative_draft, refresh_review_sources
from app.domains.skills.runtime import ConfiguredModelGateway
from app.domains.workflow.models import ReportCase, StepTask
from app.domains.workflow.service import enqueue_outbox_event, complete_step
from app.domains.content.models import CaseEvidenceItem, FindingRevision, ContentFragmentRevision, NarrativePlan
from app.domains.content.evidence import create_evidence_item, retract_case_evidence
from app.domains.reports.generation.birth_time import resolve_birth_time
from app.domains.reports.generation.mingli_foundation import calculate_mingli_foundation
from app.domains.audit.service import record_audit


async def patch_review(db, case_id, step_key, actor, payload):
    case, step, state = await review_context(db, case_id, step_key, actor, write=True)
    await require_fingerprint(db, case, step, state, payload.fingerprint)
    if payload.narrative is not None:
        await edit_narrative_draft(db, case_id, step, payload.narrative, actor.id)
    if payload.birth_time_confirmation is not None:
        if step_key != "S1":
            raise ValueError("birth_time_step_invalid")
        profile = (case.application_snapshot or {}).get("profile") or {}
        confirmation = payload.birth_time_confirmation
        time = resolve_birth_time(profile, confirmation)
        if time["status"] == "NEEDS_CONFIRMATION":
            raise ValueError("birth_time_confirmation_required")
        foundation = calculate_mingli_foundation({**profile, "review_time_policy": True, "birth_time_confirmation": confirmation})
        existing = list(await db.scalars(select(CaseEvidenceItem).where(CaseEvidenceItem.report_case_id == case_id, CaseEvidenceItem.status == "ACTIVE")))
        same_calculation = any(isinstance(row.value_json, dict) and row.value_json.get("birth_time", {}).get("adopted_datetime") == time.get("adopted_datetime") and row.value_json.get("birth_time", {}).get("basis") == time.get("basis") and row.value_json.get("birth_time", {}).get("actual_utc") == time.get("actual_utc") for row in existing)
        for row in existing:
            if not same_calculation and isinstance(row.value_json, dict) and row.value_json.get("calculation_version") == "mingli-v2":
                await retract_case_evidence(db, report_case_id=case_id, evidence_key=row.evidence_key, reason="birth_time_basis_changed")
        if not same_calculation:
            await create_evidence_item(db, report_case_id=case_id, evidence_key=f"calculated.mingli_foundation.v2.time.{fingerprint(time)[:24]}", source_type="SYSTEM_CALCULATED", source_ref="tool:birth-time-v1", value=foundation, created_by=actor.id)
            await enqueue_outbox_event(db, aggregate_type="report_case", aggregate_id=case_id, event_type="report.node.prepare", payload={"report_case_id": case_id, "step_task_id": step.id, "activation_no": step.activation_no, "retry_key": fingerprint(time)[:24]})
        state = await save_metadata(db, case_id, step_key, {"birth_time_confirmation": confirmation})
    for change in payload.changes:
        await edit_draft(db, case_id, step, change, actor.id)
    if payload.core_review is not None:
        if step_key != "S1":
            raise ValueError("node_core_review_step_invalid")
        await save_metadata(db, case_id, step_key, {"core_review": payload.core_review})
    if payload.birth_time_confirmation is not None and payload.birth_time_confirmation.get("confirmed"):
        await record_automatic_checkpoint(db, case, step, actor, "birth_data", "birth_time_confirmation")
    await record_audit(db, actor.id, "report.node.draft.save", "report_case", str(case_id), details={"step_key": step_key, "keys": [c.get("key") for c in payload.changes]})
    await db.commit()


async def record_automatic_checkpoint(db, case, step, actor, checkpoint_key, source):
    state = await db.scalar(select(NodeReviewState).where(
        NodeReviewState.report_case_id == case.id,
        NodeReviewState.step_key == step.step_key,
    ))
    snapshot = await node_snapshot(db, case, step, state)
    version = checkpoint_fingerprint(snapshot, checkpoint_key)
    existing = await db.scalar(select(NodeCheckpointApproval).where(
        NodeCheckpointApproval.report_case_id == case.id,
        NodeCheckpointApproval.step_task_id == step.id,
        NodeCheckpointApproval.activation_no == step.activation_no,
        NodeCheckpointApproval.checkpoint_key == checkpoint_key,
        NodeCheckpointApproval.fingerprint == version,
        NodeCheckpointApproval.policy_version == POLICY_VERSION,
    ))
    if existing:
        return existing
    record = NodeCheckpointApproval(
        report_case_id=case.id, step_task_id=step.id, activation_no=step.activation_no,
        checkpoint_key=checkpoint_key, fingerprint=version, policy_version=POLICY_VERSION,
        idempotency_key=f"auto:{step.id}:{step.activation_no}:{checkpoint_key}:{version}",
        manifest_json={"scope": checkpoint_scope(snapshot, checkpoint_key), "source": source,
                       "requested_node_fingerprint": fingerprint(snapshot)},
        approved_by=actor.id, approved_at=utc_now_naive(),
    )
    db.add(record)
    await db.flush()
    await record_audit(db, actor.id, "report.node.checkpoint.approve", "report_case", str(case.id),
                       details={"step_key": step.step_key, "checkpoint_key": checkpoint_key,
                                "fingerprint": version, "approval_id": record.id, "source": source})
    return record


async def approve_checkpoint(db, case_id, step_key, actor, payload):
    case, step, state = await review_context(db, case_id, step_key, actor, write=True)
    if payload.checkpoint_key not in required_checkpoint_keys(step_key):
        raise ValueError("node_checkpoint_invalid")
    prior = await db.scalar(select(NodeCheckpointApproval).where(
        NodeCheckpointApproval.report_case_id == case_id,
        NodeCheckpointApproval.idempotency_key == payload.idempotency_key,
    ))
    if prior:
        requested = (prior.manifest_json or {}).get("requested_node_fingerprint")
        if prior.step_task_id != step.id or prior.checkpoint_key != payload.checkpoint_key or requested != payload.fingerprint:
            raise ValueError("node_checkpoint_idempotency_conflict")
        return prior
    snapshot = await require_fingerprint(db, case, step, state, payload.fingerprint)
    checkpoint_key = payload.checkpoint_key
    final_quality = None
    if step_key == "S6" and checkpoint_key == "report":
        from app.application.report_quality import quality_state
        final_quality = await quality_state(db, case)
        if not final_quality.can_approve:
            raise ValueError("final_qa_issues_open_or_stale")
    final_quality_snapshot = final_quality.model_dump(mode="json") if final_quality else None
    states = await checkpoint_state_map(db, case, step, snapshot, final_quality_snapshot)

    prerequisite = {
        "findings": "birth_data" if step_key == "S1" else None,
        "analysis": "findings",
        "report": "narrative" if step_key == "S5" else None,
    }.get(checkpoint_key)
    if prerequisite and not states.get(prerequisite, {}).get("current"):
        raise ValueError("node_checkpoint_prerequisite_required")

    if checkpoint_key == "birth_data":
        if not (snapshot.get("metadata", {}).get("birth_time_confirmation") or {}).get("confirmed"):
            raise ValueError("birth_time_confirmation_required")
    elif checkpoint_key == "findings":
        if step_key == "S1":
            core_review = (snapshot.get("metadata") or {}).get("core_review") or {}
            if not all(core_review.get(key) is True for key in ("hour_pillar", "pattern_and_useful_gods")):
                raise ValueError("node_core_review_required")
        findings = list(await db.scalars(select(FindingRevision).where(
            FindingRevision.report_case_id == case_id,
            FindingRevision.owner_step_task_id == step.id,
            FindingRevision.is_current.is_(True),
            FindingRevision.status.not_in(["REJECTED", "SUPERSEDED"]),
        ).with_for_update()))
        if not findings:
            raise ValueError("node_findings_required")
        for row in findings:
            if row.status == "PROPOSED":
                row.status = "CONFIRMED"
    elif checkpoint_key == "analysis":
        rows = list(await db.scalars(select(ContentFragmentRevision).where(
            ContentFragmentRevision.report_case_id == case_id,
            ContentFragmentRevision.owner_step_task_id == step.id,
            ContentFragmentRevision.fragment_type == "ANALYSIS",
            ContentFragmentRevision.is_current.is_(True),
            ContentFragmentRevision.status == "PROPOSED",
        ).with_for_update()))
        if not snapshot["fragments"] or any(item["status"] == "STALE" for item in snapshot["fragments"]):
            raise ValueError("node_analysis_required_or_stale")
        for row in rows:
            row.status = "CONFIRMED"
    elif checkpoint_key == "narrative":
        plan = await db.scalar(select(NarrativePlan).where(
            NarrativePlan.report_case_id == case_id, NarrativePlan.is_current.is_(True),
        ).with_for_update())
        if not plan or plan.status != "CONFIRMED":
            raise ValueError("node_narrative_confirmation_required")
    elif checkpoint_key == "report":
        if not snapshot["fragments"] or any(item["status"] == "STALE" for item in snapshot["fragments"]):
            raise ValueError("node_report_required_or_stale")
        if step_key == "S5":
            readiness = snapshot.get("report_generation") or {}
            coherence = readiness.get("coherence") or {}
            if readiness.get("status") != "READY_FOR_REVIEW" or coherence.get("status") != "PASSED":
                raise ValueError("node_report_coherence_required")
        if step_key == "S6":
            if not final_quality or not final_quality.can_approve:
                raise ValueError("final_qa_issues_open_or_stale")
        rows = list(await db.scalars(select(ContentFragmentRevision).where(
            ContentFragmentRevision.report_case_id == case_id,
            ContentFragmentRevision.is_current.is_(True),
            ContentFragmentRevision.fragment_type == "REPORT",
            ContentFragmentRevision.status == "PROPOSED",
        ).with_for_update()))
        for row in rows:
            row.status = "CONFIRMED"

    await db.flush()
    snapshot = await node_snapshot(db, case, step, state)
    version = checkpoint_fingerprint(snapshot, checkpoint_key, final_quality=final_quality_snapshot)
    scope = checkpoint_scope(snapshot, checkpoint_key, final_quality=final_quality_snapshot)
    record = NodeCheckpointApproval(
        report_case_id=case_id, step_task_id=step.id, activation_no=step.activation_no,
        checkpoint_key=checkpoint_key, fingerprint=version, policy_version=POLICY_VERSION,
        idempotency_key=payload.idempotency_key,
        manifest_json={"scope": scope, "requested_node_fingerprint": payload.fingerprint},
        approved_by=actor.id, approved_at=utc_now_naive(),
    )
    db.add(record)
    await db.flush()
    await record_audit(db, actor.id, "report.node.checkpoint.approve", "report_case", str(case_id),
                       details={"step_key": step_key, "checkpoint_key": checkpoint_key,
                                "fingerprint": version, "approval_id": record.id})
    await db.commit()
    return record


async def queue_review_command(db, case_id, step_key, actor, payload, kind):
    case, step, state = await review_context(db, case_id, step_key, actor, write=True)
    prior = await db.scalar(select(NodeReviewCommand).where(NodeReviewCommand.report_case_id == case_id, NodeReviewCommand.idempotency_key == payload.idempotency_key))
    if prior:
        if prior.kind != kind or prior.step_task_id != step.id or prior.input_json.get("requested_fingerprint", prior.fingerprint) != payload.fingerprint:
            raise ValueError("node_command_idempotency_conflict")
        return prior
    snapshot = await require_fingerprint(db, case, step, state, payload.fingerprint)
    if kind == "CHECK":
        await refresh_review_sources(db, case_id, step)
        snapshot = await node_snapshot(db, case, step, state)
    targets = list(getattr(payload, "targets", []) or [])
    instruction = str(getattr(payload, "instruction", "") or "").strip()
    if kind == "REVISION":
        editable = {f["fragment_key"] for f in snapshot["fragments"]} | {f["finding_key"] for f in snapshot["findings"] if f["owner_step_task_id"] == step.id}
        if not instruction or not targets or not set(targets).issubset(editable):
            raise ValueError("node_revision_targets_invalid")
    command = NodeReviewCommand(report_case_id=case_id, step_task_id=step.id, kind=kind, idempotency_key=payload.idempotency_key,
                                activation_no=step.activation_no, fingerprint=fingerprint(snapshot), policy_version=POLICY_VERSION,
                                status="PENDING", input_json={"snapshot": snapshot, "prompt": CHECK_PROMPT if kind == "CHECK" else REVISION_PROMPT,
                                                            "targets": targets, "instruction": instruction, "requested_fingerprint": payload.fingerprint}, requested_by=actor.id, created_at=utc_now_naive())
    db.add(command)
    await db.flush()
    await enqueue_outbox_event(db, aggregate_type="node_review", aggregate_id=command.id, event_type="report.node.command", payload={"command_id": command.id})
    await db.commit()
    return command


async def execute_review_command(db, command_id, *, gateway=None):
    command = await db.scalar(select(NodeReviewCommand).where(NodeReviewCommand.id == command_id).with_for_update())
    if not command or command.status != "PENDING":
        return command
    case = await db.scalar(select(ReportCase).where(ReportCase.id == command.report_case_id).with_for_update())
    step = await db.get(StepTask, command.step_task_id)
    _, _, state = await review_context(db, case.id, step.step_key)
    async def current():
        return case.status == "ACTIVE" and case.review_policy_version == command.policy_version and step.status == "IN_REVIEW" and step.activation_no == command.activation_no and fingerprint(await node_snapshot(db, case, step, state)) == command.fingerprint
    if not await current():
        command.status = "STALE"
        await db.commit()
        return command
    command.status = "RUNNING"
    await db.commit()
    try:
        snapshot = command.input_json["snapshot"]
        if command.kind == "PREPARE":
            from app.application.node_review_automation import prepare_node
            status = await prepare_node(db, case.id, step.id, step.activation_no, retry_key=str(command.id))
            command.output_json = {"preparation_status": status}
            command.status = "COMPLETED"
            await db.commit()
            return command
        if command.kind == "CHECK" and step.step_key == "S6":
            from app.application.report_quality import queue_case_quality_run
            result = await queue_case_quality_run(db, report_case=case, actor_id=command.requested_by, idempotency_key=f"node-final-check:{command.id}", step_task=step)
            validator = result.get("validator_run")
            command.output_json = {"validator_run_id": validator.id if validator else None, "qa_fingerprint": result.get("qa_fingerprint"), "issues": program_issues(snapshot)}
            command.status = "RUNNING" if validator and validator.status in {"PENDING", "RUNNING"} else "COMPLETED"
            await db.commit()
            return command
        data = {"node": snapshot, "targets": command.input_json["targets"], "instruction": command.input_json["instruction"]}
        completion = await (gateway or ConfiguredModelGateway()).complete(system_prompt=command.input_json["prompt"], user_prompt=json.dumps(data, ensure_ascii=False, default=str), model_policy={"temperature": 0.1, "max_tokens": 8000, "thinking": False, "timeout_seconds": 240})
        raw = completion.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        output = json.loads(raw)
        command.model_trace = completion.trace
        # Refresh after releasing the lock during the provider call.
        await db.refresh(case, with_for_update=True)
        await db.refresh(step)
        if state:
            await db.refresh(state)
        if not await current():
            command.status = "STALE"
            command.output_json = {"archived_output": output}
        elif command.kind == "CHECK":
            issues, rejected = normalize_ai_issues(output, snapshot)
            if rejected and not issues:
                command.output_json = {"rejected_issues": rejected}
                raise ValueError("node_check_source_invalid")
            if rejected:
                issues.append({
                    "id": fingerprint(["node_check_quote_rejected", len(rejected), [item.get("target_key") for item in rejected if isinstance(item, dict)]])[:16],
                    "severity": "MINOR", "type": "node_check_quote_rejected", "target_key": None,
                    "message": f"有 {len(rejected)} 条自动审核意见因引用无法逐字定位，未纳入本次问题清单；如反复出现，请重新检查完整节点。",
                    "source": "AI", "status": "OPEN",
                })
            command.output_json = {"issues": program_issues(snapshot) + issues, "rejected_issues": rejected}
            command.status = "COMPLETED"
        else:
            texts = source_texts(snapshot)
            changes = output.get("changes")
            if not isinstance(changes, list) or not changes or len({c.get("key") for c in changes if isinstance(c, dict)}) != len(changes):
                raise ValueError("node_revision_output_invalid")
            for change in changes:
                if change.get("key") not in command.input_json["targets"] or not isinstance(change.get("content"), str) or not change["content"].strip():
                    raise ValueError("node_revision_output_invalid")
                change["before"] = texts[change["key"]]
            command.output_json = {"changes": changes}
            command.status = "COMPLETED"
    except Exception as error:
        command.status = "FAILED"
        command.error = str(error)[:500] if isinstance(error, (ValueError, json.JSONDecodeError)) else type(error).__name__
    command.completed_at = utc_now_naive()
    await db.commit()
    return command


async def apply_revision(db, case_id, step_key, command_id, actor, expected):
    case, step, state = await review_context(db, case_id, step_key, actor, write=True)
    command = await db.get(NodeReviewCommand, command_id)
    if not command or command.report_case_id != case_id or command.step_task_id != step.id or command.kind != "REVISION":
        raise ValueError("node_revision_not_found")
    if command.status == "APPLIED":
        return command
    snapshot = await require_fingerprint(db, case, step, state, expected)
    if command.status != "COMPLETED" or command.fingerprint != expected or command.activation_no != step.activation_no:
        raise ValueError("node_revision_stale")
    fragment_keys = {f["fragment_key"] for f in snapshot["fragments"]}
    for change in command.output_json["changes"]:
        await edit_draft(db, case_id, step, {**change, "kind": "fragment" if change["key"] in fragment_keys else "finding"}, actor.id)
    command.status = "APPLIED"
    await record_audit(db, actor.id, "report.node.revision.apply", "report_case", str(case_id), details={"command_id": command.id, "step_key": step_key})
    await db.commit()
    return command


async def current_review_check(db, case_id, step, check_id, expected):
    check = await db.get(NodeReviewCommand, check_id)
    if not check or check.report_case_id != case_id or check.step_task_id != step.id or check.kind != "CHECK" or check.status != "COMPLETED" or check.fingerprint != expected:
        raise ValueError("node_check_stale")
    return check


def apply_issue_resolution(issue, *, resolution, reason, actor_id):
    issue.update(status=resolution, resolution=reason, resolved_by=actor_id, resolved_at=utc_now_naive().isoformat())


async def resolve_review_issue(db, case_id, step_key, actor, payload):
    case, step, state = await review_context(db, case_id, step_key, actor, write=True)
    await require_fingerprint(db, case, step, state, payload.fingerprint)
    check = await current_review_check(db, case_id, step, payload.check_id, payload.fingerprint)
    if step_key == "S6" and payload.issue_id.startswith("qa:"):
        from app.application.report_quality import close_case_qa_issue
        await close_case_qa_issue(db, report_case_id=case.id, issue_id=int(payload.issue_id[3:]), actor_id=actor.id,
                                 status="ACCEPTED" if payload.resolution == "RETAINED" else "DISMISSED", resolution=payload.reason)
        await db.commit()
        return
    result = deepcopy(check.output_json)
    issue = next((i for i in result["issues"] if i["id"] == payload.issue_id), None)
    if not issue or not payload.reason.strip() or payload.resolution not in {"RETAINED", "FALSE_POSITIVE"} or issue["severity"] == "BLOCK":
        raise ValueError("node_issue_resolution_invalid")
    apply_issue_resolution(issue, resolution=payload.resolution, reason=payload.reason.strip(), actor_id=actor.id)
    check.output_json = result
    await record_audit(db, actor.id, "report.node.issue.resolve", "report_case", str(case_id), details={"check_id": check.id, "issue_id": issue["id"], "resolution": issue["status"], "reason": payload.reason})
    await db.commit()


async def resolve_review_issues(db, case_id, step_key, actor, payload):
    """同类问题整体处理：一次填写依据，逐条保留处理记录与审计。"""
    case, step, state = await review_context(db, case_id, step_key, actor, write=True)
    await require_fingerprint(db, case, step, state, payload.fingerprint)
    check = await current_review_check(db, case_id, step, payload.check_id, payload.fingerprint)
    reason = payload.reason.strip()
    resolution = payload.resolution
    issue_ids = list(dict.fromkeys(str(item) for item in payload.issue_ids if str(item).strip()))
    if not reason or resolution not in {"RETAINED", "FALSE_POSITIVE"} or not issue_ids:
        raise ValueError("node_issue_resolution_invalid")
    qa_ids, other_ids = [], issue_ids
    if step_key == "S6":
        qa_ids = [int(item[3:]) for item in issue_ids if item.startswith("qa:")]
        other_ids = [item for item in issue_ids if not item.startswith("qa:")]
    if other_ids:
        result = deepcopy(check.output_json)
        issues = result.get("issues") or []
        for issue_id in other_ids:
            issue = next((i for i in issues if i["id"] == issue_id), None)
            if not issue or issue["severity"] == "BLOCK":
                raise ValueError("node_issue_resolution_invalid")
            apply_issue_resolution(issue, resolution=resolution, reason=reason, actor_id=actor.id)
            await record_audit(db, actor.id, "report.node.issue.resolve", "report_case", str(case_id), details={"check_id": check.id, "issue_id": issue["id"], "resolution": issue["status"], "reason": reason, "grouped": True})
        check.output_json = result
    if qa_ids:
        from app.application.report_quality import close_case_qa_issues
        await close_case_qa_issues(db, report_case_id=case.id, issue_ids=qa_ids, actor_id=actor.id,
                                   status="ACCEPTED" if resolution == "RETAINED" else "DISMISSED", resolution=reason)
    await db.commit()


async def sign_node(db, case, step, state, actor, expected):
    snapshot = await require_fingerprint(db, case, step, state, expected)
    final_quality = None
    if step.step_key == "S6":
        from app.application.report_quality import quality_state
        final_quality = await quality_state(db, case)
    checkpoint_states = await checkpoint_state_map(
        db,
        case,
        step,
        snapshot,
        final_quality.model_dump(mode="json") if final_quality else None,
    )
    if any(not item["current"] for item in checkpoint_states.values()):
        raise ValueError("node_checkpoint_required")
    check = await db.scalar(select(NodeReviewCommand).where(NodeReviewCommand.report_case_id == case.id, NodeReviewCommand.step_task_id == step.id, NodeReviewCommand.kind == "CHECK", NodeReviewCommand.fingerprint == expected, NodeReviewCommand.activation_no == step.activation_no).order_by(NodeReviewCommand.id.desc()).limit(1))
    if step.step_key == "S6":
        if not final_quality or not final_quality.can_approve:
            raise ValueError("final_qa_issues_open_or_stale")
        latest_run = final_quality.latest_validator_run or {}
        if latest_run.get("status") != "COMPLETED" or not latest_run.get("current") or not latest_run.get("id"):
            raise ValueError("final_qa_issues_open_or_stale")
        current_qa_fingerprint = final_quality.qa_fingerprint_current
        check_output = (check.output_json or {}) if check else {}
        if (
            not check
            or check.status != "COMPLETED"
            or check_output.get("validator_run_id") != latest_run["id"]
            or check_output.get("qa_fingerprint") != current_qa_fingerprint
        ):
            now = utc_now_naive()
            check = NodeReviewCommand(
                report_case_id=case.id,
                step_task_id=step.id,
                kind="CHECK",
                idempotency_key=f"final-signoff-check:{case.id}:{step.activation_no}:{expected}:{latest_run['id']}",
                activation_no=step.activation_no,
                fingerprint=expected,
                policy_version=POLICY_VERSION,
                status="COMPLETED",
                input_json={"snapshot": snapshot, "prompt": CHECK_PROMPT, "targets": [], "instruction": "", "requested_fingerprint": expected, "final_signoff_binding": True},
                output_json={"validator_run_id": latest_run["id"], "qa_fingerprint": current_qa_fingerprint, "issues": program_issues(snapshot)},
                requested_by=actor.id,
                created_at=now,
                completed_at=now,
            )
            db.add(check)
            await db.flush()
    elif not check or check.status != "COMPLETED" or approval_blockers((check.output_json or {}).get("issues", [])):
        raise ValueError("node_check_required_or_issues_open")
    approval = NodeApproval(report_case_id=case.id, step_task_id=step.id, activation_no=step.activation_no, fingerprint=expected, policy_version=POLICY_VERSION,
                            check_command_id=check.id, manifest_json={"content": snapshot, "check": check.output_json, **({"final_quality": final_quality.model_dump(mode="json")} if final_quality else {})}, approved_by=actor.id, approved_at=utc_now_naive())
    db.add(approval)
    await db.flush()
    # Publish the signed version in the same transaction; there are no generated human signatures.
    for model in (FindingRevision, ContentFragmentRevision):
        owner_condition = (model.fragment_type == "REPORT") if model == ContentFragmentRevision and step.step_key == "S6" else model.owner_step_task_id == step.id
        rows = await db.scalars(select(model).where(model.report_case_id == case.id, model.is_current.is_(True), owner_condition, model.status == "PROPOSED"))
        for row in rows:
            row.status = "CONFIRMED"
    if step.step_key == "S5":
        plan = await db.scalar(select(NarrativePlan).where(NarrativePlan.report_case_id == case.id, NarrativePlan.is_current.is_(True)))
        if plan:
            plan.status, plan.confirmed_by, plan.confirmed_at = "CONFIRMED", actor.id, utc_now_naive()
    await record_audit(db, actor.id, "report.node.approve", "report_case", str(case.id), details={"step_key": step.step_key, "approval_id": approval.id, "fingerprint": expected})
    return approval


async def approve_review(db, case_id, step_key, actor, expected):
    if step_key == "S6":
        raise ValueError("use_approve_and_deliver")
    case, step, state = await review_context(db, case_id, step_key, actor)
    from app.domains.workflow.authorization import validate_step_actor
    validate_step_actor(step, actor)
    if step.status == "COMPLETED":
        prior = await db.scalar(select(NodeApproval).where(NodeApproval.report_case_id == case_id, NodeApproval.step_task_id == step.id, NodeApproval.activation_no == step.activation_no, NodeApproval.fingerprint == expected))
        if prior:
            return prior
    case, step, state = await review_context(db, case_id, step_key, actor, write=True)
    approval = await sign_node(db, case, step, state, actor, expected)
    await complete_step(db, case_id, step_key, result_json={"node_approval_id": approval.id, "fingerprint": expected, "review_policy_version": POLICY_VERSION})
    await db.commit()
    return approval
