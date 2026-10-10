from datetime import datetime
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.v1.report_cases import _workflow_error
from app.api.v1.report_cases import router as report_case_router
from app.application import report_delivery
from app.db.base import Base
from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
    NarrativePlan,
)
from app.domains.content.evidence import create_evidence_item
from app.domains.content.findings import create_finding_revision
from app.domains.content.fragments import create_content_fragment_revision
from app.domains.content.narrative import semantic_source_snapshot
from app.domains.content.queries import load_case_semantic_model
from app.domains.delivery import assembler
from app.domains.delivery.assembler import assemble_report_version
from app.domains.delivery.models import ReportVersion
from app.domains.quality.models import QAIssue
from app.domains.quality.service import resolve_qa_issue
from app.domains.skills.models import AISkillVersion, SkillRun, SkillExample
from app.domains.quality.scorecard import RUBRIC
from app.domains.review.models import NodeReviewState, NodeReviewCommand, NodeApproval
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowVersion,
    WorkflowOutbox,
)


class SessionAdapter:
    def __init__(self, session):
        self.session = session

    @property
    def new(self):
        return self.session.new

    @property
    def dirty(self):
        return self.session.dirty

    @property
    def deleted(self):
        return self.session.deleted

    def add(self, value):
        self.session.add(value)

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def get(self, model, identity):
        return self.session.get(model, identity)

    async def flush(self, objects=None):
        self.session.flush(objects=objects)

    async def commit(self):
        self.session.commit()

    async def refresh(self, value):
        self.session.refresh(value)

    def begin_nested(self):
        return AsyncNestedContext(self.session.begin_nested())


class AsyncNestedContext:
    def __init__(self, transaction):
        self.transaction = transaction

    async def __aenter__(self):
        self.transaction.__enter__()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return self.transaction.__exit__(exc_type, exc, traceback)


@pytest.fixture
def quality_db():
    tables = [
        ReportCase.__table__,
        WorkflowVersion.__table__,
        WorkflowInstance.__table__,
        StepTask.__table__,
        WorkflowOutbox.__table__,
        AISkillVersion.__table__,
        SkillRun.__table__,
        SkillExample.__table__,
        CaseEvidenceItem.__table__,
        FindingRevision.__table__,
        ContentFragmentRevision.__table__,
        NarrativePlan.__table__,
        QAIssue.__table__,
        ReportVersion.__table__,
        NodeReviewState.__table__, NodeReviewCommand.__table__, NodeApproval.__table__,
    ]
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine, expire_on_commit=False) as session:
        yield SessionAdapter(session)
    engine.dispose()


class StubGateway:
    def __init__(self, content):
        self.content = content
        self.calls = 0

    async def complete(self, *, system_prompt, user_prompt, model_policy):
        self.calls += 1
        return SimpleNamespace(
            content=self.content,
            trace={"provider": "test", "model": "stub", "latency_ms": 1},
        )


@pytest.mark.asyncio
async def test_programmatic_qa_persists_blocking_findings_for_incomplete_case(
    quality_db,
):
    from app.domains.quality.service import run_programmatic_qa

    now = datetime.utcnow()
    report_case = ReportCase(
        user_id=41,
        status="ACTIVE",
        application_snapshot={"profile": {"name": "林女士"}, "context": {}},
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    quality_db.add(report_case)
    await quality_db.flush()

    issues, fingerprint, _snapshot = await run_programmatic_qa(
        quality_db, report_case, actor_id=6
    )

    assert fingerprint
    assert any(issue.severity == "BLOCK" for issue in issues)
    assert any(issue.issue_type == "NARRATIVE_PLAN_UNCONFIRMED" for issue in issues)


@pytest.mark.asyncio
async def test_current_report_coherence_context_omits_stale_chapter_checks(quality_db):
    from app.application.report_generation import (
        _chapter_snapshot,
        _coherence_fingerprint,
        _fragment_snapshot,
        _load_authored_fragments,
        current_report_coherence_context,
    )

    now = datetime.utcnow()
    report_case = ReportCase(
        user_id=43,
        status="ACTIVE",
        application_snapshot={"profile": {"name": "林女士"}, "context": {}},
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    quality_db.add(report_case)
    await quality_db.flush()
    from app.domains.skills.service import ensure_default_narrative_skill_versions, create_skill_run
    candidate_skill = (await ensure_default_narrative_skill_versions(quality_db))[0]
    selected_run, _ = await create_skill_run(quality_db, skill_version_id=candidate_skill.id, idempotency_key="coherence-plan-source", input_snapshot={}, context_snapshot={}, report_case_id=report_case.id)
    selected_run.status = "COMPLETED"
    plan = NarrativePlan(
        report_case_id=report_case.id,
        version_no=1,
        is_current=True,
        status="CONFIRMED",
        selected_skill_run_id=selected_run.id,
        selected_candidate_key="coherence-test",
        plan_json={
            "content_plan": {
                "fragments": [
                    {
                        "fragment_key": "report.identity",
                        "chapter": "identity",
                        "sequence_no": 1,
                    }
                ]
            }
        },
        source_snapshot={},
        created_at=now,
        confirmed_at=now,
    )
    quality_db.add(plan)
    await quality_db.flush()
    fragment = await create_content_fragment_revision(
        quality_db,
        report_case_id=report_case.id,
        fragment_key="report.identity",
        fragment_type="REPORT",
        title="你是谁",
        content="你重视稳定，也希望保留自主空间。",
        status="CONFIRMED",
        source_narrative_plan_id=plan.id,
    )
    rows = await _load_authored_fragments(quality_db, report_case.id, plan)
    snapshot = _fragment_snapshot(plan, rows)
    identity_fingerprint = _coherence_fingerprint(
        plan,
        _chapter_snapshot(plan.plan_json["content_plan"], snapshot, "identity"),
    )
    report_fingerprint = _coherence_fingerprint(plan, snapshot)
    plan.plan_json = {
        **plan.plan_json,
        "generation": {
            "coherence": {"status": "PASSED", "fingerprint": report_fingerprint},
            "chapter_checks": {
                "identity": {
                    "status": "PASSED",
                    "fingerprint": identity_fingerprint,
                },
                "challenge": {"status": "BLOCKED", "fingerprint": "old-version"},
            },
            "issues": [
                {"scope": "CHAPTER", "chapter_key": "identity", "message": "current chapter issue"},
                {"scope": "CHAPTER", "chapter_key": "challenge"},
                {"scope": "REPORT", "message": "current report issue"},
            ],
        },
    }

    current = await current_report_coherence_context(quality_db, report_case.id)
    assert set(current["chapter_checks"]) == {"identity"}
    assert current["coherence"]["status"] == "PASSED"
    assert [issue.get("message") for issue in current["issues"]] == [
        "current chapter issue",
        "current report issue"
    ]

    await create_content_fragment_revision(
        quality_db,
        report_case_id=report_case.id,
        fragment_key=fragment.fragment_key,
        fragment_type="REPORT",
        title=fragment.title,
        content="你重视稳定，也希望逐步扩大自主空间。",
        status="CONFIRMED",
        edit_kind="STYLE",
        source_narrative_plan_id=plan.id,
    )
    stale = await current_report_coherence_context(quality_db, report_case.id)

    assert stale["chapter_checks"] == {}
    assert stale["coherence"]["status"] == "STALE"
    assert stale["issues"] == []


@pytest.mark.asyncio
async def test_quality_state_hides_validator_issues_for_a_stale_report_fingerprint(
    quality_db,
):
    from app.application.report_quality import quality_state
    from app.domains.skills.service import create_skill_run

    now = datetime.utcnow()
    report_case = ReportCase(
        user_id=44,
        status="ACTIVE",
        application_snapshot={"profile": {"name": "林女士"}, "context": {}},
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    quality_db.add(report_case)
    await quality_db.flush()
    validator = AISkillVersion(
        skill_key="report.final_validator",
        name="Final Validator",
        category="VALIDATOR",
        version=1,
        status="PUBLISHED",
        specification_json={"identity": {"skill_key": "report.final_validator"}},
        created_at=now,
    )
    quality_db.add(validator)
    await quality_db.flush()
    run, _ = await create_skill_run(
        quality_db,
        skill_version_id=validator.id,
        idempotency_key="stale-quality-state-run",
        input_snapshot={},
        context_snapshot={"qa_fingerprint": "old-report-version"},
        run_type="VALIDATE",
        target_type="REPORT_QA",
        target_key="report.final",
        report_case_id=report_case.id,
    )
    run.status = "COMPLETED"
    run.completed_at = now
    quality_db.add(
        QAIssue(
            report_case_id=report_case.id,
            source_type="VALIDATOR",
            source_ref_id=run.id,
            issue_type="SAFETY_LANGUAGE",
            severity="BLOCK",
            status="OPEN",
            message="This issue belongs to an older report version.",
            created_at=now,
        )
    )

    state = await quality_state(quality_db, report_case)

    assert all(issue.source_type != "VALIDATOR" for issue in state.issues)
    assert state.can_approve is False


@pytest.mark.asyncio
async def test_block_rework_and_qa_rerun_reaches_pass_with_stub_gateway(
    quality_db, monkeypatch
):
    from app.application.report_quality import (
        case_can_be_delivered,
        queue_case_quality_run,
        quality_state,
    )
    from app.application import skill_runtime
    from app.domains.skills.service import create_skill_run

    now = datetime.utcnow()
    report_case = ReportCase(
        user_id=45,
        status="ACTIVE",
        application_snapshot={
            "profile": {
                "name": "林女士",
                "birth_year": 1992,
                "birth_month": 2,
                "birth_day": 29,
                "calendar_type": "solar",
                "birth_place": "杭州",
            },
            "context": {"current_challenge": "考虑转变职业方向。"},
        },
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    quality_db.add(report_case)
    await quality_db.flush()
    authoring_skill = AISkillVersion(
        skill_key="report.narrative_plan",
        name="Narrative",
        category="AUTHORING",
        version=1,
        status="PUBLISHED",
        specification_json={"identity": {"skill_key": "report.narrative_plan"}},
        created_at=now,
    )
    quality_db.add(authoring_skill)
    await quality_db.flush()
    candidate_run, _ = await create_skill_run(
        quality_db,
        skill_version_id=authoring_skill.id,
        idempotency_key="qa-cycle-candidate-run",
        input_snapshot={},
        context_snapshot={},
        run_type="INITIAL",
        target_type="NARRATIVE_CANDIDATES",
        target_key="S5",
        report_case_id=report_case.id,
    )
    evidence = await create_evidence_item(
        quality_db,
        report_case_id=report_case.id,
        evidence_key="input.context.current_challenge",
        source_type="USER_PROVIDED",
        source_ref="application_snapshot.context.current_challenge",
        value="考虑转变职业方向。",
    )
    finding = await create_finding_revision(
        quality_db,
        report_case_id=report_case.id,
        finding_key="finding.core",
        claim="用户正在权衡稳定与自主。",
        semantic_role="CONFLICT",
        confidence="MEDIUM",
        importance="MEDIUM",
        reportability="RECOMMENDED",
        status="CONFIRMED",
        evidence_refs=[evidence.evidence_key],
        source_skill_run_id=candidate_run.id,
    )
    semantic_model = await load_case_semantic_model(quality_db, report_case.id)
    plan = NarrativePlan(
        report_case_id=report_case.id,
        version_no=1,
        is_current=True,
        status="CONFIRMED",
        selected_skill_run_id=candidate_run.id,
        selected_candidate_key="candidate_a",
        plan_json={"core_theme": "先理解取舍，再选择方向"},
        source_snapshot=semantic_source_snapshot(semantic_model),
        created_at=now,
        confirmed_at=now,
    )
    quality_db.add(plan)
    await quality_db.flush()
    identity = await create_content_fragment_revision(
        quality_db,
        report_case_id=report_case.id,
        fragment_key="report.identity",
        fragment_type="REPORT",
        title="你是谁",
        content="你注定发财，也重视自主空间。",
        status="CONFIRMED",
        finding_refs=[finding.finding_key],
        evidence_refs=[evidence.evidence_key],
        source_skill_run_id=candidate_run.id,
        source_narrative_plan_id=plan.id,
    )
    for key, title, content in (
        ("report.challenge", "卡在哪", "稳定与自主之间需要更多信息来权衡。"),
        ("report.direction", "往哪去", "可以先用小步尝试验证新的方向。"),
    ):
        await create_content_fragment_revision(
            quality_db,
            report_case_id=report_case.id,
            fragment_key=key,
            fragment_type="REPORT",
            title=title,
            content=content,
            status="CONFIRMED",
            finding_refs=[finding.finding_key],
            evidence_refs=[evidence.evidence_key],
            source_skill_run_id=candidate_run.id,
            source_narrative_plan_id=plan.id,
        )

    blocked = await queue_case_quality_run(
        quality_db,
        report_case=report_case,
        actor_id=8,
        idempotency_key="qa-cycle-blocked",
    )
    assert blocked["status"] == "PROGRAMMATIC_BLOCKED"
    assert any(issue.severity == "BLOCK" for issue in blocked["issues"])
    assert await case_can_be_delivered(quality_db, report_case) is False

    await create_content_fragment_revision(
        quality_db,
        report_case_id=report_case.id,
        fragment_key=identity.fragment_key,
        fragment_type="REPORT",
        title="你是谁",
        content="你重视自主空间，也会认真衡量稳定带来的支持。",
        status="CONFIRMED",
        finding_refs=[finding.finding_key],
        evidence_refs=[evidence.evidence_key],
        source_skill_run_id=candidate_run.id,
        source_narrative_plan_id=plan.id,
        edit_kind="SEMANTIC",
    )
    rerun = await queue_case_quality_run(
        quality_db,
        report_case=report_case,
        actor_id=8,
        idempotency_key="qa-cycle-pass",
    )
    assert rerun["status"] == "PENDING"
    assert (
        rerun["validator_run"].context_snapshot["model_policy_override"]["max_tokens"]
        >= 16000
    )
    gateway = StubGateway(json.dumps({"issues": [], "scorecard": {"dimensions": {key: {"score": maximum, "reason": "核对测试报告片段", "fragment_keys": ["report.identity"]} for key, maximum in RUBRIC.items()}}}))
    monkeypatch.setattr(skill_runtime, "DeepSeekGateway", lambda: gateway)
    completed = await skill_runtime.execute_skill_run_record(
        quality_db, rerun["validator_run"].id
    )
    state = await quality_state(quality_db, report_case)

    assert completed.status == "COMPLETED"
    assert gateway.calls == 1
    assert state.quality_status == "COMPLETED"
    assert state.latest_validator_run["current"] is True
    assert state.open_count == 0
    assert state.issues == []
    assert state.can_approve is True
    assert await case_can_be_delivered(quality_db, report_case) is True

    with pytest.raises(ValueError, match="quality_feedback_source_required"):
        await queue_case_quality_run(
            quality_db,
            report_case=report_case,
            actor_id=8,
            idempotency_key="qa-cycle-feedback-without-source",
            runtime_instruction="请重新核对全文。",
        )

    feedback_queued = await queue_case_quality_run(
        quality_db,
        report_case=report_case,
        actor_id=8,
        idempotency_key="qa-cycle-feedback",
        runtime_instruction="请复核全文是否把解释性假设写成确定事实。",
        source_run_id=completed.id,
    )
    feedback_run = feedback_queued["validator_run"]
    assert feedback_run.status == "PENDING"
    assert feedback_run.runtime_instruction == "请复核全文是否把解释性假设写成确定事实。"
    assert feedback_run.context_snapshot["quality_feedback_source_run_id"] == completed.id
    assert feedback_run.input_snapshot["context"]["feedback_rerun"]["source_run_id"] == completed.id
    assert feedback_run.input_snapshot["context"]["feedback_rerun"]["previous_ai_output"] == completed.output_parsed

    with pytest.raises(ValueError, match="quality_feedback_source_invalid"):
        await queue_case_quality_run(
            quality_db,
            report_case=report_case,
            actor_id=8,
            idempotency_key="qa-cycle-invalid-feedback",
            runtime_instruction="来源不匹配的反馈。",
            source_run_id=candidate_run.id,
        )

    feedback_completed = await skill_runtime.execute_skill_run_record(
        quality_db, feedback_run.id
    )
    state = await quality_state(quality_db, report_case)
    assert feedback_completed.status == "COMPLETED"
    assert gateway.calls == 2
    assert state.latest_validator_run["feedback_source_run_id"] == completed.id
    assert state.latest_validator_run["runtime_instruction"] == feedback_run.runtime_instruction
    assert state.can_approve is True

    workflow_version = WorkflowVersion(
        workflow_key="report.production",
        name="Consultant workflow",
        version=2,
        status="PUBLISHED",
        definition_json={"steps": []},
        created_at=now,
        published_at=now,
    )
    quality_db.add(workflow_version)
    await quality_db.flush()
    instance = WorkflowInstance(
        report_case_id=report_case.id,
        workflow_version_id=workflow_version.id,
        status="COMPLETED",
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=now,
    )
    quality_db.add(instance)
    await quality_db.flush()
    report_case.workflow_instance_id = instance.id
    report_case.status = "READY_TO_DELIVER"
    gate_result = {
        "final_gate_approved": True,
        "validator_run_id": feedback_completed.id,
        "qa_fingerprint": state.qa_fingerprint_current,
        "attested_by": 8,
        "attested_at": now.isoformat(),
    }
    quality_db.add(
        StepTask(
            workflow_instance_id=instance.id,
            step_key="S6",
            sequence_no=6,
            executor="HUMAN",
            status="COMPLETED",
            activation_no=1,
            config_snapshot={},
            result_json=gate_result,
            completed_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    await quality_db.flush()

    class ReportStub:
        def __init__(self, **values):
            self.values = values
            self.id = 701

    added_reports = []
    add_to_session = quality_db.add

    def add_delivery_record(value):
        if isinstance(value, ReportStub):
            added_reports.append(value)
        else:
            add_to_session(value)

    monkeypatch.setattr(quality_db, "add", add_delivery_record)
    monkeypatch.setattr(report_delivery, "Report", ReportStub)
    monkeypatch.setattr(report_delivery, "record_audit", AsyncMock())
    delivered_version = await report_delivery.deliver_report_case(
        quality_db,
        report_case=report_case,
        actor=SimpleNamespace(id=8, role="admin"),
    )

    assert report_case.status == "DELIVERED"
    assert len(added_reports) == 1
    assert added_reports[0].values["birth_place"] == "杭州"
    assert delivered_version.semantic_snapshot["quality"]["open_count"] == 0
    assert any(
        issue["severity"] == "BLOCK"
        and issue["status"] == "RESOLVED"
        and issue["resolution"]
        for issue in delivered_version.semantic_snapshot["quality"]["issues"]
    )
    assert any(
        item["id"] == candidate_run.id
        and item["target_type"] == "NARRATIVE_CANDIDATES"
        for item in delivered_version.semantic_snapshot["skill_runs"]
    )
    assert any(
        item["id"] == completed.id
        and item["target_type"] == "REPORT_QA"
        and item["model_trace"]["model"] == "stub"
        for item in delivered_version.semantic_snapshot["skill_runs"]
    )
    assert any(
        item["id"] == feedback_completed.id
        and item["target_type"] == "REPORT_QA"
        for item in delivered_version.semantic_snapshot["skill_runs"]
    )


@pytest.mark.asyncio
async def test_final_report_assembler_requires_approved_s6_gate():
    now = datetime.utcnow()
    case = SimpleNamespace(
        id=9, status="READY_TO_DELIVER", workflow_instance_id=12
    )
    instance = WorkflowInstance(
        id=12,
        report_case_id=9,
        workflow_version_id=3,
        status="COMPLETED",
        created_at=now,
        updated_at=now,
    )

    class Session:
        added = []

        async def get(self, model, identity):
            assert model is WorkflowInstance
            return instance

        async def scalar(self, statement):
            return None

        def add(self, value):
            self.added.append(value)

    db = Session()
    with pytest.raises(ValueError, match="final_gate_approval_required"):
        await assemble_report_version(db, case, actor_id=5)
    assert db.added == []


@pytest.mark.asyncio
async def test_assembler_rejects_an_advisory_override_outside_the_fast_path():
    """Only import-review-v1 may deliver over open findings."""
    now = datetime.utcnow()
    case = SimpleNamespace(
        id=11,
        status="READY_TO_DELIVER",
        workflow_instance_id=13,
        review_policy_version="six-node-review-v1",
    )
    instance = WorkflowInstance(
        id=13,
        report_case_id=11,
        workflow_version_id=3,
        status="COMPLETED",
        created_at=now,
        updated_at=now,
    )
    final_gate = StepTask(
        workflow_instance_id=13,
        step_key="S6",
        sequence_no=6,
        executor="HUMAN",
        status="COMPLETED",
        activation_no=1,
        config_snapshot={},
        result_json={
            "final_gate_approved": True,
            "advisory_only": True,
            "validator_run_id": 42,
            "qa_fingerprint": "qa-fingerprint-42",
        },
        created_at=now,
        updated_at=now,
    )

    class Session:
        async def get(self, model, identity):
            assert model is WorkflowInstance
            return instance

        async def scalar(self, statement):
            return final_gate

    db = Session()
    with pytest.raises(ValueError, match="final_qa_issues_open_or_stale"):
        await assemble_report_version(
            db,
            case,
            actor_id=5,
            quality_snapshot={
                "can_approve": False,
                "advisory_only": True,
                "validator_run_id": 42,
                "qa_fingerprint": "qa-fingerprint-42",
            },
        )


@pytest.mark.asyncio
async def test_assembled_report_version_captures_s6_attestation(
    quality_db, monkeypatch
):
    from app.domains.skills.service import create_skill_run

    now = datetime.utcnow()
    workflow_version = WorkflowVersion(
        workflow_key="report.production",
        name="Workflow",
        version=1,
        status="PUBLISHED",
        definition_json={"steps": []},
        created_at=now,
        published_at=now,
    )
    quality_db.add(workflow_version)
    await quality_db.flush()
    case = ReportCase(
        user_id=42,
        status="READY_TO_DELIVER",
        application_snapshot={"profile": {"name": "林女士"}},
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    quality_db.add(case)
    await quality_db.flush()
    instance = WorkflowInstance(
        report_case_id=case.id,
        workflow_version_id=workflow_version.id,
        status="COMPLETED",
        created_at=now,
        updated_at=now,
    )
    quality_db.add(instance)
    await quality_db.flush()
    case.workflow_instance_id = instance.id
    skill_version = AISkillVersion(
        skill_key="report.narrative_plan",
        name="Narrative planner",
        category="AUTHORING",
        version=1,
        status="PUBLISHED",
        specification_json={"prompt": "frozen prompt"},
        created_at=now,
    )
    quality_db.add(skill_version)
    await quality_db.flush()
    candidate_run, _ = await create_skill_run(
        quality_db,
        skill_version_id=skill_version.id,
        idempotency_key="delivery-candidate-run",
        input_snapshot={"context": {"goal": "understand"}},
        context_snapshot={"semantic_source_snapshot": {}},
        run_type="INITIAL",
        target_type="NARRATIVE_CANDIDATES",
        target_key="S5",
        report_case_id=case.id,
    )
    writer_run, _ = await create_skill_run(
        quality_db,
        skill_version_id=skill_version.id,
        idempotency_key="delivery-writer-run",
        input_snapshot={"context": {"fragment": "identity"}},
        context_snapshot={"source_narrative_plan_id": 1},
        run_type="INITIAL",
        target_type="REPORT_FRAGMENT",
        target_key="report.identity",
        report_case_id=case.id,
    )
    writer_run.status = "COMPLETED"
    writer_run.output_raw = "source output"
    writer_run.output_parsed = {"status": "READY_FOR_REVIEW"}
    writer_run.selected_examples = [
        {
            "example_id": 51,
            "version_no": 4,
            "example_snapshot": {"teaching_points": ["保持边界表达"]},
        }
    ]
    writer_run.model_trace = {"provider": "test", "model": "stub-v1"}
    validator_run, _ = await create_skill_run(
        quality_db,
        skill_version_id=skill_version.id,
        idempotency_key="delivery-validator-run",
        input_snapshot={"context": {"qa": "passed"}},
        context_snapshot={"qa_fingerprint": "qa-fingerprint-31"},
        run_type="VALIDATE",
        target_type="REPORT_QA",
        target_key="report.final",
        report_case_id=case.id,
    )
    validator_run.status = "COMPLETED"
    validator_run.model_trace = {"provider": "test", "model": "validator-v1"}
    await quality_db.flush()
    gate_result = {
        "final_gate_approved": True,
        "validator_run_id": validator_run.id,
        "qa_fingerprint": "qa-fingerprint-31",
        "attested_by": 8,
        "attested_at": now.isoformat(),
    }
    quality_db.add(
        StepTask(
            workflow_instance_id=instance.id,
            step_key="S6",
            sequence_no=6,
            executor="HUMAN",
            status="COMPLETED",
            activation_no=2,
            config_snapshot={},
            result_json=gate_result,
            completed_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    plan = NarrativePlan(
        report_case_id=case.id,
        version_no=1,
        is_current=True,
        status="CONFIRMED",
        selected_skill_run_id=candidate_run.id,
        selected_candidate_key="candidate-1",
        plan_json={"core_theme": "先稳住节奏"},
        source_snapshot={},
        created_at=now,
        confirmed_at=now,
    )
    quality_db.add(plan)
    await quality_db.flush()
    quality_db.add(
        ContentFragmentRevision(
            report_case_id=case.id,
            fragment_key="report.identity",
            revision_no=1,
            semantic_revision=1,
            content_revision=1,
            fragment_type="REPORT",
            title="我是谁",
            content="先稳住节奏。",
            status="CONFIRMED",
            source_snapshot={},
            edit_kind="STYLE",
            is_current=True,
            source_skill_run_id=writer_run.id,
            source_narrative_plan_id=plan.id,
            created_at=now,
        )
    )
    monkeypatch.setattr(
        assembler,
        "load_case_semantic_model",
        AsyncMock(return_value={"findings": [], "analysis_fragments": [], "evidence": []}),
    )

    with pytest.raises(ValueError, match="final_qa_issues_open_or_stale"):
        await assemble_report_version(quality_db, case, actor_id=8)

    version = await assemble_report_version(
        quality_db,
        case,
        actor_id=8,
        quality_snapshot={
            "can_approve": True,
            "quality_status": "COMPLETED",
            "qa_fingerprint": "qa-fingerprint-31",
            "blocking_count": 0,
            "open_count": 0,
            "validator_run_id": validator_run.id,
            "issues": [
                {
                    "id": 19,
                    "severity": "BLOCK",
                    "status": "RESOLVED",
                    "resolution": "已修订对应报告片段。",
                }
            ],
        },
        skill_run_snapshot=await report_delivery.snapshot_case_skill_runs(
            quality_db, case.id
        ),
    )

    assert version.semantic_snapshot["final_gate"]["result_json"] == gate_result
    assert version.semantic_snapshot["final_gate"]["activation_no"] == 2
    assert version.semantic_snapshot["quality"]["issues"][0]["status"] == "RESOLVED"
    writer_snapshot = next(
        row
        for row in version.semantic_snapshot["skill_runs"]
        if row["id"] == writer_run.id
    )
    assert writer_snapshot["skill_version"]["version"] == 1
    assert writer_snapshot["skill_version"]["specification_json"] == {
        "prompt": "frozen prompt"
    }
    assert writer_snapshot["selected_examples"][0]["version_no"] == 4
    assert writer_snapshot["model_trace"]["model"] == "stub-v1"
    assert version.semantic_snapshot["workflow"]["version"] == 1
    assert version.semantic_snapshot["workflow"]["definition"] == {"steps": []}

    quality_db.add(
        AISkillVersion(
            skill_key=skill_version.skill_key,
            name=skill_version.name,
            category=skill_version.category,
            version=2,
            status="PUBLISHED",
            specification_json={"prompt": "released later"},
            created_at=datetime.utcnow(),
        )
    )
    quality_db.add(
        WorkflowVersion(
            workflow_key=workflow_version.workflow_key,
            name=workflow_version.name,
            version=2,
            status="PUBLISHED",
            definition_json={"steps": [{"step_key": "S7"}]},
            created_at=datetime.utcnow(),
            published_at=datetime.utcnow(),
        )
    )
    await quality_db.flush()
    assert writer_snapshot["skill_version"]["version"] == 1
    assert version.semantic_snapshot["workflow"]["version"] == 1

    writer_run.model_trace = {"provider": "test", "model": "changed-after-delivery"}
    await quality_db.flush()
    assert writer_snapshot["model_trace"]["model"] == "stub-v1"


@pytest.mark.asyncio
async def test_validator_skill_uses_stub_gateway_and_persists_issues(
    quality_db, monkeypatch
):
    from app.application import skill_runtime
    from app.domains.skills.service import (
        create_skill_run,
        ensure_default_validator_skill_version,
    )

    skill = await ensure_default_validator_skill_version(quality_db)
    now = datetime.utcnow()
    fragment = ContentFragmentRevision(
        report_case_id=71,
        fragment_key="report.identity",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        fragment_type="REPORT",
        title="我是谁",
        content="有边界的描述。",
        status="CONFIRMED",
        source_snapshot={},
        edit_kind="SEMANTIC",
        is_current=True,
        created_at=now,
    )
    quality_db.add(fragment)
    await quality_db.flush()
    run, created = await create_skill_run(
        quality_db,
        skill_version_id=skill.id,
        idempotency_key="qa-validator-stub-1",
        input_snapshot={
            "profile": {"name": "林女士"},
            "context": {"qa_input": {"report_fragments": []}},
        },
        context_snapshot={"qa_fingerprint": "fingerprint-1"},
        run_type="VALIDATE",
        target_type="REPORT_QA",
        target_key="report.final",
        report_case_id=71,
    )
    gateway = StubGateway(
        '{"issues":[{"issue_type":"UNSUPPORTED_CLAIM","severity":"BLOCK",'
        '"message":"需要核对事实依据。","evidence":"片段缺少支持。",'
        '"suggestion":"补充来源。","target_fragment_key":"report.identity"}]}'
    )
    monkeypatch.setattr(skill_runtime, "DeepSeekGateway", lambda: gateway)

    completed = await skill_runtime.execute_skill_run_record(quality_db, run.id)
    issue = await quality_db.scalar(
        select(QAIssue).where(QAIssue.source_ref_id == run.id)
    )

    assert created is True
    assert completed.status == "COMPLETED"
    assert gateway.calls == 1
    assert issue.severity == "BLOCK"
    assert issue.target_fragment_revision_id == fragment.id


@pytest.mark.asyncio
async def test_blocking_qa_issue_cannot_be_accepted(quality_db):
    issue = QAIssue(
        report_case_id=72,
        source_type="PROGRAMMATIC",
        issue_type="MISSING_SECTION",
        severity="BLOCK",
        status="OPEN",
        message="必须补齐章节。",
        evidence_json={},
        created_at=datetime.utcnow(),
    )
    quality_db.add(issue)
    await quality_db.flush()

    with pytest.raises(ValueError, match="qa_block_cannot_be_accepted"):
        await resolve_qa_issue(
            quality_db,
            report_case_id=72,
            issue_id=issue.id,
            status="ACCEPTED",
            resolution="已有其他说明。",
            actor_id=5,
        )


def test_report_version_rejects_mutation(quality_db):
    version = ReportVersion(
        report_case_id=73,
        version_no=1,
        workflow_version_id=1,
        narrative_plan_id=1,
        fragment_snapshot=[],
        semantic_snapshot={},
        structured_data={},
        rendered_html="<article></article>",
        created_at=datetime.utcnow(),
        delivered_at=datetime.utcnow(),
    )
    quality_db.add(version)
    quality_db.session.flush()

    version.rendered_html = "<article>changed</article>"
    with pytest.raises(ValueError, match="report_version_immutable"):
        quality_db.session.flush()


def test_validator_in_progress_is_a_conflict():
    with pytest.raises(HTTPException) as raised:
        _workflow_error(ValueError("validator_run_in_progress"))
    assert raised.value.status_code == 409


@pytest.mark.asyncio
async def test_report_version_history_is_staff_only():
    route = next(
        route
        for route in report_case_router.routes
        if getattr(route, "path", None) == "/{case_id}/versions"
    )
    role_check = route.dependant.dependencies[0].call

    with pytest.raises(HTTPException) as denied:
        await role_check(current_user=SimpleNamespace(role="user", is_active=True))
    assert denied.value.status_code == 403
    assert (
        await role_check(
            current_user=SimpleNamespace(role="consultant", is_active=True)
        )
    ).role == "consultant"


@pytest.mark.asyncio
async def test_recheck_keeps_retained_programmatic_issue_decision(
    quality_db, monkeypatch
):
    """An unchanged programmatic finding must not reopen work on every re-check."""
    from app.domains.quality import service as quality_service
    from app.domains.quality.service import resolve_qa_issue

    now = datetime.utcnow()
    report_case = ReportCase(
        user_id=93,
        status="ACTIVE",
        application_snapshot={"profile": {"name": "测试用户"}, "context": {}},
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    quality_db.add(report_case)
    await quality_db.flush()

    async def collect_fake_issues(db, case):
        return (
            [
                {
                    "issue_type": "FINDING_OVER_REPEATED",
                    "severity": "MINOR",
                    "target_fragment_key": "report.identity",
                    "target_fragment_revision_id": None,
                    "message": "同一专业判断被多段引用。",
                    "evidence_json": {"evidence": "重复引用。"},
                    "suggestion": "核对各段作用。",
                }
            ],
            "fingerprint-1",
            {"fragments": []},
        )

    monkeypatch.setattr(
        quality_service, "collect_programmatic_issues", collect_fake_issues
    )

    first, _, _ = await quality_service.run_programmatic_qa(
        quality_db, report_case, actor_id=1
    )
    assert [row.status for row in first] == ["OPEN"]

    await resolve_qa_issue(
        quality_db,
        report_case_id=report_case.id,
        issue_id=first[0].id,
        status="ACCEPTED",
        resolution="各段分别用于介绍、解释与行动，保留。",
        actor_id=8,
    )

    second, _, _ = await quality_service.run_programmatic_qa(
        quality_db, report_case, actor_id=1
    )
    assert [row.status for row in second] == ["ACCEPTED"]
    assert second[0].resolution == "各段分别用于介绍、解释与行动，保留。"
    assert second[0].resolved_by == 8
    assert second[0].evidence_json["carried_from_issue_id"] == first[0].id


@pytest.mark.asyncio
async def test_recheck_reopens_programmatic_issue_after_content_change(
    quality_db, monkeypatch
):
    """A finding tied to a changed fragment revision must be judged again."""
    from app.domains.quality import service as quality_service
    from app.domains.quality.service import resolve_qa_issue

    now = datetime.utcnow()
    report_case = ReportCase(
        user_id=94,
        status="ACTIVE",
        application_snapshot={"profile": {"name": "测试用户"}, "context": {}},
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    quality_db.add(report_case)
    await quality_db.flush()

    revisions = {"id": 11}

    async def collect_fake_issues(db, case):
        return (
            [
                {
                    "issue_type": "FINDING_OVER_REPEATED",
                    "severity": "MINOR",
                    "target_fragment_key": "report.identity",
                    "target_fragment_revision_id": revisions["id"],
                    "message": "同一专业判断被多段引用。",
                    "evidence_json": {"evidence": "重复引用。"},
                    "suggestion": "核对各段作用。",
                }
            ],
            "fingerprint-1",
            {"fragments": []},
        )

    monkeypatch.setattr(
        quality_service, "collect_programmatic_issues", collect_fake_issues
    )

    first, _, _ = await quality_service.run_programmatic_qa(
        quality_db, report_case, actor_id=1
    )
    await resolve_qa_issue(
        quality_db,
        report_case_id=report_case.id,
        issue_id=first[0].id,
        status="DISMISSED",
        resolution="程序化启发式误报。",
        actor_id=8,
    )

    revisions["id"] = 12
    second, _, _ = await quality_service.run_programmatic_qa(
        quality_db, report_case, actor_id=1
    )
    assert [row.status for row in second] == ["OPEN"]


async def _validator_recheck_case(quality_db, *, user_id: int):
    from app.domains.skills.service import create_skill_run

    now = datetime.utcnow()
    report_case = ReportCase(
        user_id=user_id,
        status="ACTIVE",
        application_snapshot={"profile": {"name": "测试用户"}, "context": {}},
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    quality_db.add(report_case)
    validator = AISkillVersion(
        skill_key="report.final_validator",
        name="Final Validator",
        category="VALIDATOR",
        version=1,
        status="PUBLISHED",
        specification_json={"identity": {"skill_key": "report.final_validator"}},
        created_at=now,
    )
    quality_db.add(validator)
    await quality_db.flush()
    fragment = ContentFragmentRevision(
        report_case_id=report_case.id,
        fragment_key="report.identity",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        fragment_type="REPORT",
        title="我是谁",
        content="有边界的描述。",
        status="CONFIRMED",
        source_snapshot={},
        edit_kind="SEMANTIC",
        is_current=True,
        created_at=now,
    )
    quality_db.add(fragment)
    await quality_db.flush()

    async def queue_run(key: str):
        run, _ = await create_skill_run(
            quality_db,
            skill_version_id=validator.id,
            idempotency_key=key,
            input_snapshot={},
            context_snapshot={"qa_fingerprint": f"fingerprint-{key}"},
            run_type="VALIDATE",
            target_type="REPORT_QA",
            target_key="report.final",
            report_case_id=report_case.id,
        )
        run.status = "COMPLETED"
        run.completed_at = datetime.utcnow()
        run.output_parsed = {
            "issues": [
                {
                    "issue_type": "SAFETY_LANGUAGE",
                    "severity": "MINOR",
                    "message": "该句缺少待验证限定。",
                    "evidence": "有边界的描述。",
                    "suggestion": "补充待验证限定。",
                    "target_fragment_key": "report.identity",
                }
            ]
        }
        await quality_db.flush()
        return run

    return report_case, fragment, queue_run


@pytest.mark.asyncio
async def test_validator_recheck_keeps_decision_for_unchanged_fragment(quality_db):
    from app.domains.quality.service import replace_validator_issues, resolve_qa_issue

    report_case, _fragment, queue_run = await _validator_recheck_case(
        quality_db, user_id=95
    )
    first_run = await queue_run("validator-carry-1")
    first = await replace_validator_issues(quality_db, first_run)
    assert [row.status for row in first] == ["OPEN"]

    await resolve_qa_issue(
        quality_db,
        report_case_id=report_case.id,
        issue_id=first[0].id,
        status="ACCEPTED",
        resolution="该句已由上下文限定，保留。",
        actor_id=8,
    )

    second_run = await queue_run("validator-carry-2")
    second = await replace_validator_issues(quality_db, second_run)
    assert [row.status for row in second] == ["ACCEPTED"]
    assert second[0].resolution == "该句已由上下文限定，保留。"
    assert second[0].resolved_by == 8
    assert second[0].evidence_json["carried_from_issue_id"] == first[0].id


@pytest.mark.asyncio
async def test_validator_recheck_reopens_decision_after_fragment_revision_changes(
    quality_db,
):
    from app.domains.quality.service import replace_validator_issues, resolve_qa_issue

    report_case, fragment, queue_run = await _validator_recheck_case(
        quality_db, user_id=96
    )
    first_run = await queue_run("validator-reopen-1")
    first = await replace_validator_issues(quality_db, first_run)
    await resolve_qa_issue(
        quality_db,
        report_case_id=report_case.id,
        issue_id=first[0].id,
        status="DISMISSED",
        resolution="启发式误报。",
        actor_id=8,
    )

    fragment.is_current = False
    replacement = ContentFragmentRevision(
        report_case_id=report_case.id,
        fragment_key="report.identity",
        revision_no=2,
        semantic_revision=2,
        content_revision=2,
        fragment_type="REPORT",
        title="我是谁",
        content="有边界的描述。",
        status="CONFIRMED",
        source_snapshot={},
        edit_kind="SEMANTIC",
        is_current=True,
        created_at=datetime.utcnow(),
    )
    quality_db.add(replacement)
    await quality_db.flush()

    second_run = await queue_run("validator-reopen-2")
    second = await replace_validator_issues(quality_db, second_run)
    assert [row.status for row in second] == ["OPEN"]
    assert second[0].target_fragment_revision_id == replacement.id


@pytest.mark.asyncio
async def test_validator_recheck_repairs_non_contiguous_evidence(quality_db):
    from app.domains.quality.service import replace_validator_issues

    report_case, _fragment, queue_run = await _validator_recheck_case(
        quality_db, user_id=97
    )
    report_case.review_policy_version = "six-node-review-v1"
    await quality_db.flush()
    run = await queue_run("validator-evidence-repair")
    run.output_parsed["issues"][0]["evidence"] = "有边界的描述。……补充转述"

    issues = await replace_validator_issues(quality_db, run)

    assert len(issues) == 1
    assert issues[0].source_type == "VALIDATOR"
    assert issues[0].evidence_json["evidence"] == "有边界的描述。"
    assert issues[0].evidence_json["evidence_original"] == "有边界的描述。……补充转述"


@pytest.mark.asyncio
async def test_validator_recheck_records_unverified_evidence_without_failing(
    quality_db,
):
    from app.domains.quality.service import replace_validator_issues

    report_case, _fragment, queue_run = await _validator_recheck_case(
        quality_db, user_id=98
    )
    report_case.review_policy_version = "six-node-review-v1"
    await quality_db.flush()
    run = await queue_run("validator-evidence-unverified")
    run.output_parsed["issues"][0]["evidence"] = "这段文字完全不在目标正文中"

    issues = await replace_validator_issues(quality_db, run)

    assert len(issues) == 1
    assert issues[0].source_type == "PROGRAMMATIC"
    assert issues[0].issue_type == "VALIDATOR_EVIDENCE_UNVERIFIED"
    assert issues[0].severity == "MINOR"
    assert issues[0].evidence_json["validator_issue_type"] == "SAFETY_LANGUAGE"
    assert issues[0].evidence_json["evidence"] == "这段文字完全不在目标正文中"


@pytest.mark.asyncio
async def test_same_type_quality_issues_close_together_with_single_records(quality_db):
    from app.application.report_quality import close_case_qa_issues
    from app.domains.quality.service import group_quality_issues

    rows = [
        QAIssue(
            report_case_id=72,
            source_type="VALIDATOR",
            issue_type="事实不一致",
            severity="MAJOR",
            status="OPEN",
            target_fragment_key=f"report.block.{index}",
            message=f"第{index}处正文未标注假设。",
            evidence_json={},
            created_at=datetime.utcnow(),
        )
        for index in range(3)
    ]
    blocking = QAIssue(
        report_case_id=72,
        source_type="VALIDATOR",
        issue_type="必须修复",
        severity="BLOCK",
        status="OPEN",
        target_fragment_key="report.block.9",
        message="必须补齐章节。",
        evidence_json={},
        created_at=datetime.utcnow(),
    )
    for row in rows:
        quality_db.add(row)
    quality_db.add(blocking)
    await quality_db.flush()

    groups = group_quality_issues(rows + [blocking])
    assert len(groups) == 1
    assert groups[0]["count"] == 3 and groups[0]["severity"] == "MAJOR"
    assert sorted(groups[0]["issue_ids"]) == sorted(row.id for row in rows)

    with pytest.raises(ValueError, match="qa_block_cannot_be_accepted"):
        await close_case_qa_issues(
            quality_db,
            report_case_id=72,
            issue_ids=[blocking.id],
            status="ACCEPTED",
            resolution="整体保留原因。",
            actor_id=5,
        )

    reason = "统一核对：三处正文均已补充假设标注，保留条件式口径。"
    resolved = await close_case_qa_issues(
        quality_db,
        report_case_id=72,
        issue_ids=[row.id for row in rows],
        status="ACCEPTED",
        resolution=reason,
        actor_id=5,
    )
    assert len(resolved) == 3
    assert all(row.status == "ACCEPTED" for row in resolved)
    assert all(row.resolution == reason for row in resolved)
    assert all(row.resolved_by == 5 and row.resolved_at is not None for row in resolved)
    assert group_quality_issues(rows) == []


@pytest.mark.asyncio
async def test_six_node_quality_run_binds_node_activation_and_materializes_findings(
    quality_db, monkeypatch
):
    """S6's whole-report check must carry the node activation it belongs to.

    The skill runtime only materializes validator findings while the owning node
    still holds that activation; without the binding the run is archived and
    every validator issue is dropped on the floor.
    """
    from app.application import report_quality, skill_runtime
    from app.application.report_quality import queue_case_quality_run
    from app.domains.skills.bindings import specification_digest
    from app.domains.skills.service import ensure_default_validator_skill_version

    now = datetime.utcnow()
    validator = await ensure_default_validator_skill_version(quality_db)
    validator_spec = validator.specification_json
    workflow_version = WorkflowVersion(
        workflow_key="report.production",
        name="Workflow",
        version=1,
        status="PUBLISHED",
        definition_json={"steps": []},
        created_at=now,
    )
    quality_db.add(workflow_version)
    await quality_db.flush()
    report_case = ReportCase(
        user_id=46,
        status="ACTIVE",
        review_policy_version="six-node-review-v1",
        application_snapshot={
            "profile": {"name": "林女士"},
            "context": {},
            "skill_bindings": {
                "report.final_validator": {
                    "id": validator.id,
                    "version": validator.version,
                    "digest": specification_digest(validator_spec),
                }
            },
        },
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    quality_db.add(report_case)
    await quality_db.flush()
    instance = WorkflowInstance(
        report_case_id=report_case.id,
        workflow_version_id=workflow_version.id,
        status="RUNNING",
        created_at=now,
        updated_at=now,
    )
    quality_db.add(instance)
    await quality_db.flush()
    report_case.workflow_instance_id = instance.id
    step = StepTask(
        workflow_instance_id=instance.id,
        step_key="S6",
        sequence_no=6,
        executor="HYBRID",
        status="IN_REVIEW",
        activation_no=1,
        config_snapshot={},
        created_at=now,
        updated_at=now,
    )
    quality_db.add(step)
    await quality_db.flush()
    from app.domains.skills.service import create_skill_run

    plan_source, _ = await create_skill_run(
        quality_db,
        skill_version_id=validator.id,
        idempotency_key="six-node-quality-plan-source",
        input_snapshot={},
        context_snapshot={},
        run_type="INITIAL",
        target_type="NARRATIVE_CANDIDATES",
        target_key="S5",
        report_case_id=report_case.id,
    )
    plan = NarrativePlan(
        report_case_id=report_case.id,
        version_no=1,
        is_current=True,
        status="PROPOSED",
        selected_skill_run_id=plan_source.id,
        selected_candidate_key="six-node-quality",
        plan_json={"core_theme": "先理解取舍，再选择方向"},
        source_snapshot={},
        created_at=now,
    )
    quality_db.add(plan)
    await quality_db.flush()
    fragment = await create_content_fragment_revision(
        quality_db,
        report_case_id=report_case.id,
        fragment_key="report.identity",
        fragment_type="REPORT",
        title="你是谁",
        content="你重视稳定，也会认真衡量自主空间。",
        status="CONFIRMED",
        source_narrative_plan_id=plan.id,
    )
    snapshot = {
        "narrative_plan": None,
        "semantic_model": {},
        "fragments": [
            {
                "fragment_key": fragment.fragment_key,
                "revision_no": fragment.revision_no,
                "title": fragment.title,
                "content": fragment.content,
                "source_snapshot": fragment.source_snapshot,
            }
        ],
    }
    monkeypatch.setattr(
        report_quality,
        "run_programmatic_qa",
        AsyncMock(
            return_value=([], "six-node-fingerprint", snapshot)
        ),
    )

    queued = await queue_case_quality_run(
        quality_db,
        report_case=report_case,
        actor_id=7,
        idempotency_key="s6-node-quality",
        step_task=step,
    )
    run = queued["validator_run"]

    assert run.step_task_id == step.id
    assert run.context_snapshot["quality_activation_no"] == step.activation_no
    assert run.context_snapshot["node_activation_no"] == step.activation_no

    gateway = StubGateway(
        json.dumps(
            {
                "issues": [
                    {
                        "severity": "MAJOR",
                        "issue_type": "SOURCE_FIDELITY",
                        "target_fragment_key": "report.identity",
                        "evidence": "你重视稳定",
                        "message": "该判断缺少用户资料支撑。",
                        "suggestion": "补充用户原始资料的核对记录。",
                    }
                ],
                "scorecard": {
                    "dimensions": {
                        key: {
                            "score": maximum,
                            "reason": "核对测试报告片段",
                            "fragment_keys": ["report.identity"],
                        }
                        for key, maximum in RUBRIC.items()
                    }
                },
            },
            ensure_ascii=False,
        )
    )
    monkeypatch.setattr(skill_runtime, "DeepSeekGateway", lambda: gateway)

    completed = await skill_runtime.execute_skill_run_record(quality_db, run.id)
    issues = list(
        await quality_db.scalars(
            select(QAIssue).where(QAIssue.report_case_id == report_case.id)
        )
    )

    assert completed.status == "COMPLETED", completed.error
    assert "node_archived" not in completed.context_snapshot
    assert [
        (row.source_type, row.severity, row.target_fragment_key) for row in issues
    ] == [("VALIDATOR", "MAJOR", "report.identity")]
