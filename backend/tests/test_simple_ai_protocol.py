"""Coverage for the AI-assisted ``report.simple`` execution protocol."""

from datetime import datetime

import pytest
from sqlalchemy import func, select

from app.application import report_cases as report_cases_application
from app.application import simple_ai_workflow
from app.application.simple_ai_workflow import (
    AI_REVISION,
    INITIAL,
    REGENERATE,
    apply_run_result,
    approve_step,
    prepare_ready_step,
    quality_state,
    record_run_failure,
    reopen_step,
    save_manual_edit,
    start_generation,
)
from app.domains.delivery.simple_models import (
    SimpleReviewDecision,
    SimpleStepExecution,
    SimpleStepRevision,
)
from app.domains.service_requests.staff import accept_service_request
from app.domains.skills.models import SkillRun
from app.domains.workflow.models import ReportCase, StepTask, WorkflowOutbox
from app.domains.workflow.service import create_report_case
from app.domains.workflow.simple_definitions import (
    SIMPLE_PROTOCOL_AI_ASSISTED,
    SIMPLE_STEP_KEYS,
)
from app.models.user import User
from tests.test_simple_report_workflow import (  # noqa: F401
    SessionAdapter,
    _AsyncContext,
    _profile_snapshot,
    simple_db,
)


async def _ai_case(db, monkeypatch, *, with_request: bool = True, steps=None):
    """Create an AI-assisted Simple case and optionally accept it."""
    if steps is not None:
        monkeypatch.setattr(simple_ai_workflow, "SIMPLE_STEP_KEYS", tuple(steps))
    version = await report_cases_application.ensure_simple_workflow_version(
        db, SIMPLE_PROTOCOL_AI_ASSISTED
    )
    request = None
    if with_request:
        from app.domains.service_requests.models import ServiceRequest

        request = ServiceRequest(
            user_id=1,
            service_type="report",
            status="submitted",
            request_payload={
                **_profile_snapshot(),
                "workflow_key": "report.simple",
                "simple_protocol": SIMPLE_PROTOCOL_AI_ASSISTED,
            },
        )
        db.add(request)
        await db.flush()
    report_case = await create_report_case(
        db,
        user_id=1,
        service_request_id=request.id if request is not None else None,
        source_report_task_id=None,
        application_snapshot=_profile_snapshot(),
        workflow_version=version,
    )
    await db.flush()
    if not with_request:
        consultant = User(
            id=7,
            phone="test-7",
            name="普通咨询师",
            role="consultant",
            is_active=True,
            consultant_type=None,
            consultant_specialties=[],
        )
        db.add(consultant)
        await db.flush()
        for task in (
            await db.scalars(
                select(StepTask)
                .where(StepTask.workflow_instance_id == report_case.workflow_instance_id)
                .order_by(StepTask.sequence_no)
            )
        ).all():
            task.assignee_id = consultant.id
        await db.flush()
        return report_case, request, consultant
    consultant = User(
        id=7,
        phone="test-7",
        name="普通咨询师",
        role="consultant",
        is_active=True,
        consultant_type=None,
        consultant_specialties=[],
    )
    db.add(consultant)
    await db.flush()
    await accept_service_request(db, request.id, consultant)
    await db.flush()
    return report_case, request, consultant


async def _task(db, report_case, step_key):
    return await db.scalar(
        select(StepTask).where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == step_key,
        )
    )


async def _execution(db, report_case, step_key):
    return await db.scalar(
        select(SimpleStepExecution).where(
            SimpleStepExecution.report_case_id == report_case.id,
            SimpleStepExecution.step_key == step_key,
        )
    )


async def _active_run(db, execution_id):
    return await db.scalar(
        select(SkillRun)
        .where(
            SkillRun.target_type == "SIMPLE_STEP",
            SkillRun.context_snapshot["simple_step_key"].as_string()
            == select(SimpleStepExecution.step_key)
            .where(SimpleStepExecution.id == execution_id)
            .scalar_subquery(),
        )
        .order_by(SkillRun.id.desc())
    )


async def _run_for_step(db, report_case, step_key):
    return await db.scalar(
        select(SkillRun)
        .where(
            SkillRun.report_case_id == report_case.id,
            SkillRun.target_type == "SIMPLE_STEP",
            SkillRun.target_key == step_key,
        )
        .order_by(SkillRun.id.desc())
    )


async def _prepare(db, report_case, step_key):
    task = await _task(db, report_case, step_key)
    result = await prepare_ready_step(
        db, report_case.id, task.id, task.activation_no
    )
    assert result == "started"
    run = await _run_for_step(db, report_case, step_key)
    assert run is not None
    return task, run


async def _complete(db, report_case, step_key, content):
    task, run = await _prepare(db, report_case, step_key)
    run.status = "COMPLETED"
    run.output_raw = content
    run.output_parsed = {"content": content}
    revision = await apply_run_result(db, run)
    await db.flush()
    assert revision is not None
    return task, revision


@pytest.mark.asyncio
async def test_ai_case_waits_for_acceptance_and_starts_on_ready_event(
    simple_db, monkeypatch
):
    report_case, request, consultant = await _ai_case(simple_db, monkeypatch)
    first_key = SIMPLE_STEP_KEYS[0]
    first_task = await _task(simple_db, report_case, first_key)

    # Creation alone must never call a model.
    assert await simple_db.scalar(select(func.count(SkillRun.id))) == 0
    assert (
        await simple_db.scalar(select(func.count(SimpleStepRevision.id))) == 0
    )
    assert (
        await simple_db.scalar(select(func.count(SimpleStepExecution.id)))
        == len(SIMPLE_STEP_KEYS)
    )
    ready_event = await simple_db.scalar(
        select(WorkflowOutbox)
        .where(
            WorkflowOutbox.event_type == "workflow.step.ready",
            WorkflowOutbox.aggregate_id == report_case.workflow_instance_id,
        )
        .order_by(WorkflowOutbox.id)
    )
    assert ready_event is not None
    await simple_db.refresh(ready_event)

    # Acceptance assigns the consultant and enqueues the ready event.
    assert request.status == "accepted"
    assert request.assigned_consultant_id == consultant.id
    assert first_task.assignee_id == consultant.id
    accepted_event = await simple_db.scalar(
        select(WorkflowOutbox)
        .where(
            WorkflowOutbox.event_type == "workflow.step.ready",
            WorkflowOutbox.payload_json["step_task_id"].as_integer()
            == first_task.id,
        )
        .order_by(WorkflowOutbox.id.desc())
    )
    assert accepted_event is not None
    assert accepted_event.payload_json["activation_no"] == first_task.activation_no

    # Only consuming the ready event creates the skill run.
    result = await prepare_ready_step(
        simple_db, report_case.id, first_task.id, first_task.activation_no
    )
    assert result == "started"
    run = await _run_for_step(simple_db, report_case, first_key)
    assert run is not None
    assert run.status == "PENDING"
    assert run.run_type == "INITIAL"
    assert run.skill_version_id == first_task.config_snapshot["skill_version_id"]
    assert run.context_snapshot["simple_protocol"] == SIMPLE_PROTOCOL_AI_ASSISTED
    assert run.context_snapshot["simple_step_key"] == first_key
    assert run.context_snapshot["simple_activation_no"] == 1
    assert run.context_snapshot["simple_assignee_id"] == consultant.id
    assert run.context_snapshot["simple_attempt_no"] == 1
    execution = await _execution(simple_db, report_case, first_key)
    assert execution.execution_status == "GENERATING"
    assert execution.active_skill_run_id == run.id
    assert first_task.status == "EXECUTING"

    # Replaying the same ready event is idempotent.
    assert (
        await prepare_ready_step(
            simple_db, report_case.id, first_task.id, first_task.activation_no
        )
        == "already_started"
    )
    assert (
        await simple_db.scalar(
            select(func.count(SkillRun.id)).where(
                SkillRun.report_case_id == report_case.id
            )
        )
        == 1
    )


@pytest.mark.asyncio
async def test_ai_revision_manual_edit_and_approval_are_immutable(
    simple_db, monkeypatch
):
    report_case, _request, consultant = await _ai_case(
        simple_db, monkeypatch, with_request=False
    )
    first_key = SIMPLE_STEP_KEYS[0]
    second_key = SIMPLE_STEP_KEYS[1]
    first_task, initial = await _complete(
        simple_db, report_case, first_key, "初版 S1"
    )

    # Feedback revision against the exact immutable revision.
    await start_generation(
        simple_db,
        case_id=report_case.id,
        step_key=first_key,
        actor=consultant,
        idempotency_key="revise-s1-1",
        mode=AI_REVISION,
        base_revision_id=initial.id,
        feedback_text="补充职业转换的现实约束",
    )
    revised_run = await _run_for_step(simple_db, report_case, first_key)
    assert revised_run.id != initial.skill_run_id
    assert revised_run.run_type == "REWRITE"
    revised_run.status = "COMPLETED"
    revised_run.output_parsed = {"content": "修订版 S1", "notes": ["补约束"]}
    revised = await apply_run_result(simple_db, revised_run)
    await simple_db.flush()
    assert revised is not None
    assert revised.revision_type == AI_REVISION
    assert revised.parent_revision_id == initial.id
    assert revised.skill_run_id == revised_run.id
    assert revised.created_by is None
    decision = await simple_db.scalar(
        select(SimpleReviewDecision).where(
            SimpleReviewDecision.idempotency_key == "decision:revise-s1-1"
        )
    )
    assert decision is not None
    assert decision.decision == "REQUEST_REVISION"
    assert decision.target_revision_id == initial.id
    assert decision.reviewer_id == consultant.id
    assert decision.review_mode == "OWNER"
    assert decision.operator_id == consultant.id
    assert decision.on_behalf_of_user_id is None

    # Manual edit appends a new immutable revision and its own decision row.
    manual = await save_manual_edit(
        simple_db,
        case_id=report_case.id,
        step_key=first_key,
        actor=consultant,
        content="人工修订版 S1",
        structured_content={"sections": ["人事"]},
        base_revision_id=revised.id,
        idempotency_key="manual-s1-1",
    )
    assert manual.revision_type == "MANUAL_EDIT"
    assert manual.parent_revision_id == revised.id
    assert manual.created_by == consultant.id
    assert manual.skill_run_id is None
    replay = await save_manual_edit(
        simple_db,
        case_id=report_case.id,
        step_key=first_key,
        actor=consultant,
        content="人工修订版 S1",
        structured_content={"sections": ["人事"]},
        base_revision_id=revised.id,
        idempotency_key="manual-s1-1",
    )
    assert replay.id == manual.id
    with pytest.raises(ValueError, match="simple_review_idempotency_conflict"):
        await save_manual_edit(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=consultant,
            content="人工修订稿被偷换",
            structured_content={"sections": ["人事"]},
            base_revision_id=revised.id,
            idempotency_key="manual-s1-1",
        )

    execution = await approve_step(
        simple_db,
        case_id=report_case.id,
        step_key=first_key,
        actor=consultant,
        base_revision_id=manual.id,
        idempotency_key="approve-s1-1",
        review_note="确认通过",
    )
    assert execution.execution_status == "COMPLETED"
    assert execution.confirmed_revision_id == manual.id
    await simple_db.refresh(first_task)
    assert first_task.status == "COMPLETED"
    assert (
        await approve_step(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=consultant,
            base_revision_id=manual.id,
            idempotency_key="approve-s1-1",
            review_note="确认通过",
        )
    ).id == execution.id

    approve_decision = await simple_db.scalar(
        select(SimpleReviewDecision).where(
            SimpleReviewDecision.idempotency_key == "approve-s1-1"
        )
    )
    assert approve_decision.decision == "APPROVE"
    assert approve_decision.target_revision_id == manual.id
    assert approve_decision.feedback_text == "确认通过"
    assert approve_decision.review_mode == "OWNER"
    assert approve_decision.operator_id == consultant.id

    # The next step is activated and can be prepared.
    await simple_db.refresh(report_case)
    second_task = await _task(simple_db, report_case, second_key)
    assert second_task.status == "READY"
    assert (
        await prepare_ready_step(
            simple_db, report_case.id, second_task.id, second_task.activation_no
        )
        == "started"
    )

    # Revisions and decisions are append-only.
    manual.content = "篡改"
    with pytest.raises(ValueError, match="simple_step_revision_immutable"):
        await simple_db.flush()
    await simple_db.rollback()
    stored = await simple_db.get(SimpleStepRevision, manual.id)
    assert stored.content == "人工修订版 S1"
    stored_decision = await simple_db.get(SimpleReviewDecision, approve_decision.id)
    stored_decision.feedback_text = "篡改"
    with pytest.raises(ValueError, match="simple_review_decision_immutable"):
        await simple_db.flush()
    await simple_db.rollback()

    # S6 exposes the validator output without hard-blocking in phase one.
    last_key = SIMPLE_STEP_KEYS[-1]
    last_task = await _task(simple_db, report_case, last_key)
    last_task.status = "READY"
    last_task.activation_no = 1
    await simple_db.flush()
    last_task, last_run = await _prepare(simple_db, report_case, last_key)
    last_run.status = "COMPLETED"
    last_run.output_parsed = {
        "content": "质量检查结论",
        "quality": {"level": "PASS"},
        "findings": [{"code": "minor", "block": False}],
    }
    assert await apply_run_result(simple_db, last_run) is not None
    await simple_db.flush()
    quality = await quality_state(simple_db, report_case.id)
    assert quality["quality"] == {"level": "PASS"}
    assert quality["validator_findings"] == [{"code": "minor", "block": False}]
    assert quality["hard_blocks"] == []


@pytest.mark.asyncio
async def test_generation_idempotency_and_command_conflicts(simple_db, monkeypatch):
    report_case, _request, consultant = await _ai_case(simple_db, monkeypatch)
    first_key = SIMPLE_STEP_KEYS[0]
    first_task = await _task(simple_db, report_case, first_key)
    await prepare_ready_step(
        simple_db, report_case.id, first_task.id, first_task.activation_no
    )
    run = await _run_for_step(simple_db, report_case, first_key)
    run.status = "COMPLETED"
    run.output_parsed = {"content": "S1 v1"}
    base = await apply_run_result(simple_db, run)
    await simple_db.flush()

    execution = await start_generation(
        simple_db,
        case_id=report_case.id,
        step_key=first_key,
        actor=consultant,
        idempotency_key="regen-A",
        mode=REGENERATE,
        base_revision_id=base.id,
        feedback_text="换一条论证路径",
    )
    replay = await start_generation(
        simple_db,
        case_id=report_case.id,
        step_key=first_key,
        actor=consultant,
        idempotency_key="regen-A",
        mode=REGENERATE,
        base_revision_id=base.id,
        feedback_text="换一条论证路径",
    )
    assert replay.id == execution.id
    assert execution.execution_status == "REVISING"
    assert (
        await simple_db.scalar(
            select(func.count(SkillRun.id)).where(
                SkillRun.report_case_id == report_case.id,
                SkillRun.run_type == "REGENERATE",
            )
        )
        == 1
    )

    # The same key with different parameters must never return unrelated work.
    with pytest.raises(ValueError, match="simple_generation_idempotency_conflict"):
        await start_generation(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=consultant,
            idempotency_key="regen-A",
            mode=REGENERATE,
            base_revision_id=base.id,
            feedback_text="偷换反馈",
        )
    with pytest.raises(ValueError, match="simple_step_run_in_progress"):
        await start_generation(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=consultant,
            idempotency_key="regen-B",
            mode=INITIAL,
        )


@pytest.mark.asyncio
async def test_stale_activation_base_owner_and_fingerprint_are_rejected(
    simple_db, monkeypatch
):
    report_case, _request, consultant = await _ai_case(simple_db, monkeypatch)
    first_key = SIMPLE_STEP_KEYS[0]
    first_task = await _task(simple_db, report_case, first_key)
    await prepare_ready_step(
        simple_db, report_case.id, first_task.id, first_task.activation_no
    )
    run = await _run_for_step(simple_db, report_case, first_key)
    run.status = "COMPLETED"
    run.output_parsed = {"content": "S1 v1"}
    base = await apply_run_result(simple_db, run)
    await simple_db.flush()
    execution = await _execution(simple_db, report_case, first_key)

    # Old owner or stale activation cannot start another command.
    other = User(
        id=8,
        phone="test-8",
        name="其他咨询师",
        role="consultant",
        is_active=True,
        consultant_type=None,
        consultant_specialties=[],
    )
    simple_db.add(other)
    await simple_db.flush()
    with pytest.raises(ValueError, match="report_case_forbidden"):
        await start_generation(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=other,
            idempotency_key="wrong-owner",
            mode=INITIAL,
        )

    execution = await _execution(simple_db, report_case, first_key)
    first_task = await _task(simple_db, report_case, first_key)
    execution.activation_no = 2
    await simple_db.flush()
    with pytest.raises(ValueError, match="simple_activation_outdated"):
        await start_generation(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=consultant,
            idempotency_key="stale-activation",
            mode=REGENERATE,
            base_revision_id=base.id,
        )
    execution.activation_no = first_task.activation_no
    await simple_db.flush()

    # Expired base revisions and forged revision ids are rejected.
    execution = await _execution(simple_db, report_case, first_key)
    with pytest.raises(ValueError, match="simple_revision_not_found"):
        await start_generation(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=consultant,
            idempotency_key="foreign-revision",
            mode=REGENERATE,
            base_revision_id=base.id + 500,
        )

    execution = await _execution(simple_db, report_case, first_key)
    revised_run = SkillRun(
        skill_version_id=run.skill_version_id,
        report_case_id=report_case.id,
        workflow_instance_id=report_case.workflow_instance_id,
        step_task_id=first_task.id,
        target_type="SIMPLE_STEP",
        target_key=first_key,
        run_type="REGENERATE",
        status="COMPLETED",
        idempotency_key="stale-base-run",
        input_snapshot={},
        context_snapshot=dict(run.context_snapshot or {}),
        output_parsed={"content": "S1 v2"},
        created_at=datetime.utcnow(),
    )
    simple_db.add(revised_run)
    await simple_db.flush()
    revised = SimpleStepRevision(
        execution_id=execution.id,
        revision_no=2,
        revision_type="REGENERATE",
        parent_revision_id=base.id,
        content="S1 v2",
        structured_content=None,
        source_revision_refs={"upstream": {}, "base_revision_id": base.id},
        skill_run_id=revised_run.id,
        created_by=None,
        idempotency_key="new-base-revision",
        created_at=datetime.utcnow(),
    )
    simple_db.add(revised)
    await simple_db.flush()
    execution.current_revision_id = revised.id
    await simple_db.flush()
    with pytest.raises(ValueError, match="simple_revision_outdated"):
        await start_generation(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=consultant,
            idempotency_key="expired-base",
            mode=REGENERATE,
            base_revision_id=base.id,
        )

    # A late result whose input fingerprint no longer matches is archived.
    execution = await _execution(simple_db, report_case, first_key)
    late_run = await _run_for_step(simple_db, report_case, first_key)
    execution.active_skill_run_id = late_run.id
    execution.execution_status = "GENERATING"
    execution.input_fingerprint = "tampered"
    late_run.status = "COMPLETED"
    await simple_db.flush()
    assert await apply_run_result(simple_db, late_run) is None
    assert late_run.context_snapshot["simple_archived"] == (
        "obsolete_activation_or_input"
    )
    assert (
        await simple_db.scalar(
            select(func.count(SimpleStepRevision.id)).where(
                SimpleStepRevision.execution_id == execution.id
            )
        )
        == 2
    )


@pytest.mark.asyncio
async def test_automatic_retry_stops_after_two_retries_then_manual_retry(
    simple_db, monkeypatch
):
    report_case, _request, consultant = await _ai_case(simple_db, monkeypatch)
    first_key = SIMPLE_STEP_KEYS[0]
    first_task, first_run = await _prepare(simple_db, report_case, first_key)

    first_run.status = "FAILED"
    first_run.error = "gateway timeout"
    await record_run_failure(simple_db, first_run)
    await simple_db.flush()
    assert (await _execution(simple_db, report_case, first_key)).execution_status == (
        "GENERATING"
    )
    retry_one = await _run_for_step(simple_db, report_case, first_key)
    assert retry_one.context_snapshot["simple_attempt_no"] == 2
    await simple_db.refresh(first_task)
    assert first_task.retry_count == 1

    retry_one.status = "FAILED"
    retry_one.error = "gateway timeout"
    await record_run_failure(simple_db, retry_one)
    await simple_db.flush()
    retry_two = await _run_for_step(simple_db, report_case, first_key)
    assert retry_two.context_snapshot["simple_attempt_no"] == 3
    await simple_db.refresh(first_task)
    assert first_task.retry_count == 2

    retry_two.status = "FAILED"
    retry_two.error = "gateway timeout"
    await record_run_failure(simple_db, retry_two)
    await simple_db.flush()
    failed = await _execution(simple_db, report_case, first_key)
    assert failed.execution_status == "FAILED"
    assert failed.active_skill_run_id is None
    assert failed.input_snapshot["last_error"] == "gateway timeout"
    await simple_db.refresh(first_task)
    assert first_task.retry_count == 2
    assert first_task.status == "READY"
    assert first_task.last_error == "gateway timeout"

    # An explicit consultant retry continues the frozen plan with a new attempt.
    await start_generation(
        simple_db,
        case_id=report_case.id,
        step_key=first_key,
        actor=consultant,
        idempotency_key="manual-retry-s1",
        mode=INITIAL,
    )
    manual_retry = await _run_for_step(simple_db, report_case, first_key)
    assert manual_retry.context_snapshot["simple_attempt_no"] == 4
    await simple_db.refresh(first_task)
    assert first_task.retry_count == 3
    assert (
        await simple_db.scalar(
            select(func.count(SkillRun.id)).where(
                SkillRun.report_case_id == report_case.id,
                SkillRun.target_type == "SIMPLE_STEP",
            )
        )
        == 4
    )


@pytest.mark.asyncio
async def test_reassignment_archives_the_previous_owners_run(simple_db, monkeypatch):
    from app.domains.workflow.service import assign_step

    report_case, _request, first_owner = await _ai_case(simple_db, monkeypatch)
    first_key = SIMPLE_STEP_KEYS[0]
    first_task = await _task(simple_db, report_case, first_key)
    await prepare_ready_step(
        simple_db, report_case.id, first_task.id, first_task.activation_no
    )
    stale_run = await _run_for_step(simple_db, report_case, first_key)
    second_owner = User(
        id=9,
        phone="test-9",
        name="接手咨询师",
        role="consultant",
        is_active=True,
        consultant_type=None,
        consultant_specialties=[],
    )
    simple_db.add(second_owner)
    await simple_db.flush()

    await assign_step(simple_db, report_case.id, first_key, second_owner.id)
    await simple_db.flush()
    await simple_db.refresh(stale_run)
    assert stale_run.context_snapshot["simple_archived"] == "assignee_reassigned"
    execution = await _execution(simple_db, report_case, first_key)
    assert execution.execution_status == "FAILED"
    assert execution.active_skill_run_id is None
    assert execution.input_snapshot["last_error"] == "simple_assignee_changed"

    # The old owner's late result cannot create a revision for the new owner.
    stale_run.status = "COMPLETED"
    stale_run.output_parsed = {"content": "旧负责人迟到的结果"}
    assert await apply_run_result(simple_db, stale_run) is None
    await simple_db.flush()
    assert (
        await simple_db.scalar(
            select(func.count(SimpleStepRevision.id)).where(
                SimpleStepRevision.execution_id == execution.id
            )
        )
        == 0
    )
    stale_run.status = "FAILED"
    stale_run.error = "旧负责人迟到失败"
    await record_run_failure(simple_db, stale_run)
    await simple_db.flush()
    assert (await _execution(simple_db, report_case, first_key)).execution_status == (
        "FAILED"
    )

    # The new owner can explicitly retry and produce the first revision.
    await start_generation(
        simple_db,
        case_id=report_case.id,
        step_key=first_key,
        actor=second_owner,
        idempotency_key="new-owner-retry",
        mode=INITIAL,
    )
    new_run = await _run_for_step(simple_db, report_case, first_key)
    assert new_run.context_snapshot["simple_assignee_id"] == second_owner.id
    new_run.status = "COMPLETED"
    new_run.output_parsed = {"content": "新负责人的结果"}
    revision = await apply_run_result(simple_db, new_run)
    await simple_db.flush()
    assert revision is not None
    assert revision.content == "新负责人的结果"


@pytest.mark.asyncio
async def test_legacy_complete_and_unimplemented_finalize_are_guarded(
    simple_db, monkeypatch
):
    from fastapi import HTTPException
    from unittest.mock import AsyncMock

    from app.api.v1 import report_cases as report_case_routes
    from app.domains.delivery.simple_schemas import SimpleStepCompleteInput

    report_case, _request, consultant = await _ai_case(simple_db, monkeypatch)
    first_key = SIMPLE_STEP_KEYS[0]
    first_task, first_run = await _prepare(simple_db, report_case, first_key)
    first_run.status = "COMPLETED"
    first_run.output_parsed = {"content": "S1 v1"}
    await apply_run_result(simple_db, first_run)
    await simple_db.flush()

    with pytest.raises(HTTPException) as error:
        await report_case_routes.complete_simple_report_case_step(
            case_id=report_case.id,
            step_key=first_key,
            data=SimpleStepCompleteInput(report_text="绕过 AI 审核"),
            request=AsyncMock(),
            current_user=consultant,
            db=simple_db,
        )
    assert error.value.status_code == 409
    assert error.value.detail == "simple_ai_protocol_required"

    with pytest.raises(HTTPException) as error:
        await report_case_routes.finalize_simple_report_case(
            case_id=report_case.id,
            current_user=consultant,
            db=simple_db,
        )
    assert error.value.status_code == 501
    assert error.value.detail == "simple_finalize_not_implemented"

    from app.main import app

    routes = {
        (path, method.upper())
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.lower() in {"get", "post"}
    }
    assert {
        ("/api/v1/report-cases/{case_id}/simple/steps/{step_key}/generate", "POST"),
        ("/api/v1/report-cases/{case_id}/simple/steps/{step_key}/revise", "POST"),
        ("/api/v1/report-cases/{case_id}/simple/steps/{step_key}/regenerate", "POST"),
        (
            "/api/v1/report-cases/{case_id}/simple/steps/{step_key}/manual-edit",
            "POST",
        ),
        ("/api/v1/report-cases/{case_id}/simple/steps/{step_key}/approve", "POST"),
        (
            "/api/v1/report-cases/{case_id}/simple/steps/{step_key}/revisions",
            "GET",
        ),
        ("/api/v1/report-cases/{case_id}/simple/steps/{step_key}/reopen", "POST"),
        ("/api/v1/report-cases/{case_id}/simple/quality", "GET"),
        ("/api/v1/report-cases/{case_id}/simple/finalize", "POST"),
    }.issubset(routes)


@pytest.mark.asyncio
async def test_reopen_invalidates_only_downstream_revisions_that_reference_it(
    simple_db, monkeypatch
):
    report_case, _request, consultant = await _ai_case(
        simple_db, monkeypatch, with_request=False
    )
    _, s1_revision = await _complete(simple_db, report_case, "S1", "S1 v1")
    await approve_step(
        simple_db,
        case_id=report_case.id,
        step_key="S1",
        actor=consultant,
        base_revision_id=s1_revision.id,
        idempotency_key="approve-s1-v1",
    )
    _, s2_revision = await _complete(simple_db, report_case, "S2", "S2 v1")
    await approve_step(
        simple_db,
        case_id=report_case.id,
        step_key="S2",
        actor=consultant,
        base_revision_id=s2_revision.id,
        idempotency_key="approve-s2-v1",
    )
    _, s3_revision = await _complete(simple_db, report_case, "S3", "S3 v1")
    await approve_step(
        simple_db,
        case_id=report_case.id,
        step_key="S3",
        actor=consultant,
        base_revision_id=s3_revision.id,
        idempotency_key="approve-s3-v1",
    )

    s2_execution = await _execution(simple_db, report_case, "S2")
    s3_execution = await _execution(simple_db, report_case, "S3")
    s4_execution = await _execution(simple_db, report_case, "S4")
    assert s2_execution.confirmed_revision_id == s2_revision.id
    assert s3_execution.confirmed_revision_id == s3_revision.id
    assert s4_execution.execution_status == "READY"
    assert s4_execution.confirmed_revision_id is None
    assert s4_execution.input_snapshot == {}

    first_execution = await _execution(simple_db, report_case, "S1")
    old_confirmed_id = first_execution.confirmed_revision_id
    reopened = await reopen_step(
        simple_db,
        case_id=report_case.id,
        step_key="S1",
        actor=consultant,
        reason="S1 需要重开",
        idempotency_key="reopen-s1-1",
    )
    assert reopened.execution_status == "READY"
    assert reopened.confirmed_revision_id is None
    assert reopened.current_revision_id is None
    assert reopened.activation_no == 2
    await simple_db.refresh(await _task(simple_db, report_case, "S1"))
    first_task = await _task(simple_db, report_case, "S1")
    assert first_task.activation_no == 2
    assert first_task.status == "READY"

    # A downstream node that consumed the replaced confirmation is invalidated.
    s2_execution = await _execution(simple_db, report_case, "S2")
    assert s2_execution.execution_status == "READY"
    assert s2_execution.dependency_status == "STALE"
    assert s2_execution.confirmed_revision_id is None
    assert s2_execution.current_revision_id is not None
    assert s2_execution.stale_reason == (
        f"upstream:S1:confirmed_revision:{old_confirmed_id}"
    )

    # S3's effective chain still references the old S1 confirmation, so its
    # confirmation is invalidated too.  A node that never consumed anything
    # (S4) must stay untouched.
    s3_execution = await _execution(simple_db, report_case, "S3")
    assert s3_execution.execution_status == "READY"
    assert s3_execution.dependency_status == "STALE"
    assert s3_execution.confirmed_revision_id is None
    assert s3_execution.current_revision_id is not None
    s4_execution = await _execution(simple_db, report_case, "S4")
    assert s4_execution.execution_status == "READY"
    assert s4_execution.dependency_status == "CURRENT"
    assert s4_execution.stale_reason is None

    # Replaying the reopen is idempotent.
    replay = await reopen_step(
        simple_db,
        case_id=report_case.id,
        step_key="S1",
        actor=consultant,
        reason="S1 需要重开",
        idempotency_key="reopen-s1-1",
    )
    assert replay.id == reopened.id
    assert replay.activation_no == 2
    reopen_decision = await simple_db.scalar(
        select(SimpleReviewDecision).where(
            SimpleReviewDecision.idempotency_key == "reopen-s1-1"
        )
    )
    assert reopen_decision.decision == "REOPEN"
    assert reopen_decision.target_revision_id == old_confirmed_id
    assert reopen_decision.feedback_text == "S1 需要重开"

    # A stale S2 can recover by regenerating against the latest confirmation.
    first_task = await _task(simple_db, report_case, "S1")
    await prepare_ready_step(
        simple_db, report_case.id, first_task.id, first_task.activation_no
    )
    first_run = await _run_for_step(simple_db, report_case, "S1")
    first_run.status = "COMPLETED"
    first_run.output_parsed = {"content": "S1 v2"}
    replacement = await apply_run_result(simple_db, first_run)
    assert replacement is not None
    await approve_step(
        simple_db,
        case_id=report_case.id,
        step_key="S1",
        actor=consultant,
        base_revision_id=replacement.id,
        idempotency_key="approve-s1-v2",
    )
    s2_task = await _task(simple_db, report_case, "S2")
    assert (
        await prepare_ready_step(
            simple_db, report_case.id, s2_task.id, s2_task.activation_no
        )
        == "started"
    )
    recovery_run = await _run_for_step(simple_db, report_case, "S2")
    assert recovery_run.context_snapshot["simple_recover_stale"] is True
    assert (
        recovery_run.input_snapshot["upstream_revisions"]["S1"]["revision_id"]
        == replacement.id
    )
    assert (await _execution(simple_db, report_case, "S2")).dependency_status == "CURRENT"
