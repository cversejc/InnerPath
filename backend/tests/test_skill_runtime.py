from datetime import datetime
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domains.skills.definitions import (
    DEFAULT_SKILL_KEY,
    default_analysis_skill_specifications,
    default_skill_specification,
    validate_skill_specification,
)
from app.domains.skills.models import AISkillVersion, SkillExample, SkillRun
from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
)
from app.domains.skills.runtime import (
    ModelCompletion,
    SkillExecutionError,
    execute_skill,
)
from app.domains.skills.service import (
    create_skill_run,
    create_skill_draft,
    ensure_default_skill_version,
    ensure_default_validator_skill_version,
    publish_skill_version,
    update_skill_draft,
)
from app.domains.skills.examples import (
    create_example_candidate,
    create_example_revision,
    publish_skill_example,
    retrieve_skill_examples,
    retire_skill_example,
    update_example_redaction,
)
from app.domains.skills.evaluation import evaluate_regression_output
from app.domains.reports.models import ReportTask
from app.domains.service_requests.models import ServiceRequest
from app.domains.workflow.definitions import (
    DEFAULT_WORKFLOW_KEY,
    default_workflow_definition,
)
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowOutbox,
    WorkflowVersion,
)
from app.domains.workflow.service import create_workflow_draft, publish_workflow_version
from app.models.user import User


class SessionAdapter:
    def __init__(self, session: Session):
        self.session = session

    def add(self, value):
        self.session.add(value)

    def add_all(self, values):
        self.session.add_all(values)

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def get(self, model, identity):
        return self.session.get(model, identity)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

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


class CaseAccessSession(SessionAdapter):
    def __init__(self, session, request_row):
        super().__init__(session)
        self.request_row = request_row

    async def scalar(self, statement):
        if statement.column_descriptions[0].get("entity") is ServiceRequest:
            return self.request_row
        return await super().scalar(statement)


class SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, traceback):
        return False


@pytest.fixture
def skill_db():
    tables = [
        AISkillVersion.__table__,
        SkillRun.__table__,
        SkillExample.__table__,
        WorkflowVersion.__table__,
        ReportCase.__table__,
        WorkflowInstance.__table__,
        StepTask.__table__,
        WorkflowOutbox.__table__,
        CaseEvidenceItem.__table__,
        ContentFragmentRevision.__table__,
        FindingRevision.__table__,
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
        self.last_request = None

    async def complete(self, *, system_prompt, user_prompt, model_policy):
        self.calls += 1
        self.last_request = (system_prompt, user_prompt, model_policy)
        return ModelCompletion(
            content=self.content,
            trace={
                "provider": "test",
                "model": "stub",
                "input_tokens": 12,
                "output_tokens": 30,
                "latency_ms": 7,
                "estimated_cost": 0,
                "finish_reason": "stop",
            },
        )


def _profile():
    return {
        "name": "林女士",
        "gender": "female",
        "birth_year": 1992,
        "birth_month": 6,
        "birth_day": 18,
        "birth_hour": 9,
        "birth_minute": 30,
        "calendar_type": "solar",
        "time_accuracy": "exact",
    }


def _report_text(extra=""):
    return (
        "## 一、我是谁\n能量类型：稳定探索型\n核心特质：认真\n\n"
        "## 二、我卡在哪\n正在梳理选择。\n\n"
        "## 三、我往哪去\n下周可以先完成一个小实验。\n\n"
        "## 五、总结与寄语\n你可以保留自己的节奏。\n" + extra
    )


@pytest.mark.asyncio
async def test_analysis_skill_accepts_only_stage_matched_evidence_references():
    specification = next(
        item
        for item in default_analysis_skill_specifications()
        if item["instructions"]["stage_key"] == "S2"
    )
    output = {
        "summary": "基于用户表达与上游结构提出可复核的心理模式假设。",
        "findings": [
            {
                "finding_key": "s2.psychology.autonomy",
                "claim": "用户希望在边界清楚时保留自主空间。",
                "kind": "FINDING",
                "semantic_role": "MOTIVATION_PATTERN",
                "confidence": "MEDIUM",
                "importance": "HIGH",
                "reportability": "RECOMMENDED",
                "evidence_refs": ["input.context.current_challenge"],
                "relation_refs": [{"finding_key": "foundation.balance", "relation": "MAPS_TO"}],
                "structured_data": {},
            }
        ],
        "analysis_fragments": [
            {
                "fragment_key": "analysis.psychology.persona",
                "title": "心理映射候选",
                "content": "在边界清楚时，用户更容易开展探索。",
                "finding_refs": ["s2.psychology.autonomy"],
                "evidence_refs": ["input.context.current_challenge"],
            }
        ],
        "risk_flags": [],
    }
    skill = SimpleNamespace(
        id=71,
        skill_key=specification["identity"]["skill_key"],
        version=1,
        specification_json=specification,
    )
    context = {
        "profile": {"name": "演示用户"},
        "context": {"current_challenge": "评估工作方向"},
        "analysis_context": {
            "step_key": "S2",
            "evidence": [
                {
                    "evidence_key": "input.context.current_challenge",
                    "source_type": "USER_PROVIDED",
                }
            ],
            "upstream_confirmed_findings": [
                {"finding_key": "foundation.balance", "claim": "重视稳定。"}
            ],
        },
    }
    gateway = StubGateway(json.dumps(output, ensure_ascii=False))
    result = await execute_skill(
        skill_version=skill,
        input_data=context,
        gateway=gateway,
    )
    assert result.output_parsed["findings"][0]["evidence_refs"] == [
        "input.context.current_challenge"
    ]
    assert "【机器可读输出契约】" in gateway.last_request[0]
    assert '"analysis_fragments"' in gateway.last_request[0]
    assert '"relation_refs"' in gateway.last_request[0]
    assert '"evidence_keys": ["input.context.current_challenge"]' in gateway.last_request[0]
    assert '"confirmed_finding_keys": ["foundation.balance"]' in gateway.last_request[0]

    context["analysis_context"]["step_key"] = "S3"
    with pytest.raises(ValueError, match="report_analysis_skill_stage_mismatch"):
        await execute_skill(
            skill_version=skill,
            input_data=context,
            gateway=StubGateway(json.dumps(output, ensure_ascii=False)),
        )


@pytest.mark.asyncio
async def test_analysis_skill_drops_finding_with_only_unsupported_evidence():
    specification = default_analysis_skill_specifications()[0]
    skill = SimpleNamespace(
        id=72,
        skill_key=specification["identity"]["skill_key"],
        version=1,
        specification_json=specification,
    )
    output = {
        "summary": "候选摘要。",
        "findings": [
            {
                "finding_key": "s1.foundation.test",
                "claim": "有依据的候选判断。",
                "kind": "SIGNAL",
                "semantic_role": "CORE_STRUCTURE",
                "confidence": "LOW",
                "importance": "MEDIUM",
                "reportability": "INTERNAL_ONLY",
                "evidence_refs": ["evidence.not.in.case"],
                "relation_refs": [],
                "structured_data": {},
            }
        ],
        "analysis_fragments": [],
        "risk_flags": [],
    }
    result = await execute_skill(
        skill_version=skill,
        input_data={
            "profile": {},
            "context": {},
            "analysis_context": {
                "step_key": "S1",
                "evidence": [{"evidence_key": "evidence.valid"}],
                "upstream_confirmed_findings": [],
            },
        },
        gateway=StubGateway(json.dumps(output, ensure_ascii=False)),
    )

    assert result.output_parsed["findings"] == []
    assert result.model_trace["reference_repairs"] == {
        "invalid_evidence_refs_removed": 1,
        "unsupported_findings_dropped": 1,
    }


@pytest.mark.asyncio
async def test_analysis_skill_keeps_valid_references_and_removes_unknown_ones():
    specification = default_analysis_skill_specifications()[1]
    skill = SimpleNamespace(
        id=73,
        skill_key=specification["identity"]["skill_key"],
        version=1,
        specification_json=specification,
    )
    output = {
        "summary": "候选摘要。",
        "findings": [
            {
                "finding_key": "s2.mapping.test",
                "claim": "有依据的候选判断。",
                "kind": "FINDING",
                "semantic_role": "MOTIVATION_PATTERN",
                "confidence": "LOW",
                "importance": "MEDIUM",
                "reportability": "RECOMMENDED",
                "evidence_refs": ["evidence.invalid", "evidence.valid"],
                "relation_refs": [
                    {"finding_key": "finding.invalid"},
                    {"finding_key": "foundation.balance"},
                ],
                "structured_data": {},
            }
        ],
        "analysis_fragments": [
            {
                "fragment_key": "s2.mapping.fragment",
                "title": "模式候选",
                "content": "基于已知信息形成的待审阅模式。",
                "finding_refs": ["s2.mapping.test", "finding.invalid"],
                "evidence_refs": ["evidence.invalid", "evidence.valid"],
            },
            {
                "fragment_key": "s2.unsupported.fragment",
                "title": "无依据片段",
                "content": "没有可验证来源的片段。",
                "finding_refs": ["finding.invalid"],
                "evidence_refs": ["evidence.invalid"],
            },
        ],
        "risk_flags": [
            {"message": "需要咨询师核实。", "references": ["finding.invalid", "evidence.valid"]},
            {"message": "无依据风险。", "references": ["finding.invalid"]},
        ],
    }
    result = await execute_skill(
        skill_version=skill,
        input_data={
            "profile": {},
            "context": {},
            "analysis_context": {
                "step_key": "S2",
                "evidence": [{"evidence_key": "evidence.valid"}],
                "upstream_confirmed_findings": [
                    {"finding_key": "foundation.balance"}
                ],
            },
        },
        gateway=StubGateway(json.dumps(output, ensure_ascii=False)),
    )

    finding = result.output_parsed["findings"][0]
    assert finding["evidence_refs"] == ["evidence.valid"]
    assert finding["relation_refs"] == [{"finding_key": "foundation.balance"}]
    assert result.output_parsed["analysis_fragments"][0]["finding_refs"] == [
        "s2.mapping.test"
    ]
    assert result.output_parsed["analysis_fragments"][0]["evidence_refs"] == [
        "evidence.valid"
    ]
    assert result.output_parsed["risk_flags"][0]["references"] == ["evidence.valid"]
    assert len(result.output_parsed["analysis_fragments"]) == 1
    assert len(result.output_parsed["risk_flags"]) == 1
    assert result.model_trace["reference_repairs"] == {
        "invalid_evidence_refs_removed": 3,
        "invalid_finding_refs_removed": 3,
        "invalid_risk_refs_removed": 2,
        "unsupported_fragments_dropped": 1,
        "unsupported_risk_flags_dropped": 1,
    }


def test_skill_specification_rejects_unregistered_tools_and_processors():
    unsupported_tool = default_skill_specification()
    unsupported_tool["tool_policy"]["allowed"] = ["python.exec"]
    with pytest.raises(ValueError, match="skill_tool_unsupported"):
        validate_skill_specification(unsupported_tool)

    unsupported_processor = default_skill_specification()
    unsupported_processor["processor_policy"]["processor"] = "arbitrary.script"
    with pytest.raises(ValueError, match="skill_processor_required"):
        validate_skill_specification(unsupported_processor)


@pytest.mark.asyncio
async def test_published_skill_version_is_immutable_and_next_draft_increments(skill_db):
    published = await ensure_default_skill_version(skill_db)
    draft = await create_skill_draft(
        skill_db,
        skill_key=DEFAULT_SKILL_KEY,
        name=published.name,
        category="AUTHORING",
        specification=published.specification_json,
        created_by=None,
    )
    assert draft.version == 2
    await publish_skill_version(skill_db, draft.id, published_by=None)

    with pytest.raises(ValueError, match="skill_version_immutable"):
        await update_skill_draft(
            skill_db,
            draft.id,
            name="Changed",
            category="AUTHORING",
            specification=draft.specification_json,
        )


@pytest.mark.asyncio
async def test_executor_projects_context_validates_output_and_records_trace():
    skill = AISkillVersion(
        id=41,
        skill_key=DEFAULT_SKILL_KEY,
        name="Report",
        category="AUTHORING",
        version=1,
        status="PUBLISHED",
        specification_json=default_skill_specification(),
    )
    gateway = StubGateway(_report_text())
    result = await execute_skill(
        skill_version=skill,
        input_data={
            "profile": _profile(),
            "context": {
                "focus_topics": ["career"],
                "current_challenge": "考虑转型",
                "expected_outcomes": ["方向指引"],
                "internal_chain_of_thought": "must not reach the model",
            },
            "other_users": [{"name": "hidden"}],
        },
        gateway=gateway,
    )

    assert result.output_parsed["basic_info"]["name"] == "林女士"
    assert result.model_trace["skill_version_id"] == 41
    assert result.model_trace["global_policy_version"] == "global-policy-v1"
    assert "must not reach the model" not in gateway.last_request[1]
    assert "other_users" not in result.context_snapshot
    assert "internal_chain_of_thought" not in result.context_snapshot["context"]
    assert result.context_snapshot["foundation_data"]


@pytest.mark.asyncio
async def test_executor_fails_guardrail_instead_of_returning_fallback_output():
    skill = AISkillVersion(
        id=42,
        skill_key=DEFAULT_SKILL_KEY,
        name="Report",
        category="AUTHORING",
        version=1,
        status="PUBLISHED",
        specification_json=default_skill_specification(),
    )
    with pytest.raises(ValueError, match="skill_guardrail_blocked"):
        await execute_skill(
            skill_version=skill,
            input_data={"profile": _profile(), "context": {}},
            gateway=StubGateway(_report_text("\n注定发财")),
        )


@pytest.mark.asyncio
async def test_skill_run_is_idempotent_and_completion_is_reused(skill_db, monkeypatch):
    from app.application import skill_runtime

    version = await ensure_default_skill_version(skill_db)
    run, created = await create_skill_run(
        skill_db,
        skill_version_id=version.id,
        idempotency_key="test-skill-run-1",
        input_snapshot={"profile": _profile(), "context": {}},
        context_snapshot={"profile": _profile(), "context": {}},
    )
    duplicate, duplicate_created = await create_skill_run(
        skill_db,
        skill_version_id=version.id,
        idempotency_key="test-skill-run-1",
        input_snapshot={"profile": _profile(), "context": {}},
        context_snapshot={"profile": _profile(), "context": {}},
    )
    assert created is True
    assert duplicate_created is False
    assert duplicate.id == run.id

    gateway = StubGateway(_report_text())
    monkeypatch.setattr(skill_runtime, "DeepSeekGateway", lambda: gateway)
    completed = await skill_runtime.execute_skill_run_record(skill_db, run.id)
    repeated = await skill_runtime.execute_skill_run_record(skill_db, run.id)
    assert completed.status == "COMPLETED"
    assert completed.output_parsed["basic_info"]["name"] == "林女士"
    assert repeated.status == "COMPLETED"
    assert gateway.calls == 1


@pytest.mark.asyncio
async def test_case_skill_run_records_calculated_foundation_as_evidence(
    skill_db, monkeypatch
):
    from app.application import skill_runtime
    from app.domains.content.service import create_evidence_item

    version = await ensure_default_skill_version(skill_db)
    report_case = ReportCase(
        user_id=19,
        status="ACTIVE",
        application_snapshot={"profile": _profile(), "context": {}},
        application_submitted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    skill_db.add(report_case)
    await skill_db.flush()
    user_evidence = await create_evidence_item(
        skill_db,
        report_case_id=report_case.id,
        evidence_key="input.profile.gender",
        source_type="USER_PROVIDED",
        source_ref="application_snapshot.profile.gender",
        value="female",
    )
    run, _created = await skill_runtime._queue_run(
        skill_db,
        version_id=version.id,
        idempotency_key="case-foundation-run-1",
        input_data={"profile": _profile(), "context": {}},
        runtime_instruction=None,
        target_type="REPORT_CASE_STEP",
        target_key="S5",
        report_case=report_case,
    )
    gateway = StubGateway(_report_text())
    monkeypatch.setattr(skill_runtime, "DeepSeekGateway", lambda: gateway)

    completed = await skill_runtime.execute_skill_run_record(skill_db, run.id)
    evidence = await skill_db.scalar(
        select(CaseEvidenceItem).where(
            CaseEvidenceItem.report_case_id == report_case.id,
            CaseEvidenceItem.evidence_key
            == f"calculated.foundation.skill_run.{run.id}",
        )
    )

    assert completed.status == "COMPLETED"
    assert evidence.source_type == "SYSTEM_CALCULATED"
    assert evidence.source_skill_run_id == run.id
    assert evidence.source_ref == f"skill_run:{run.id}:foundation_data"
    assert evidence.value_json == completed.context_snapshot["foundation_data"]
    evidence_refs = completed.context_snapshot["source_references"]["evidence"]
    assert {row["evidence_key"] for row in evidence_refs} == {
        user_evidence.evidence_key,
        evidence.evidence_key,
    }


@pytest.mark.asyncio
async def test_skill_workflow_version_pins_report_authoring_skill(skill_db):
    from app.application.skill_runtime import ensure_skill_workflow_version

    initial = await create_workflow_draft(
        skill_db,
        DEFAULT_WORKFLOW_KEY,
        "Workflow v1",
        default_workflow_definition(),
        created_by=None,
    )
    await publish_workflow_version(skill_db, initial.id, published_by=None)
    result = await ensure_skill_workflow_version(skill_db)
    authoring = next(
        step for step in result.definition_json["steps"] if step["step_key"] == "S5"
    )

    assert result.version == 2
    assert authoring["executor"] == "HYBRID"
    skill = await skill_db.get(AISkillVersion, authoring["config"]["skill_version_id"])
    assert skill.skill_key == DEFAULT_SKILL_KEY and skill.version == 1
    assert result.definition_json["skill_bindings"][DEFAULT_SKILL_KEY]["id"] == skill.id


@pytest.mark.asyncio
async def test_outbox_skill_event_executes_once_on_duplicate_delivery(
    skill_db, monkeypatch
):
    from app.application import skill_runtime
    from app.tasks import workflow_tasks

    version = await ensure_default_skill_version(skill_db)
    run, _created = await create_skill_run(
        skill_db,
        skill_version_id=version.id,
        idempotency_key="outbox-skill-run-1",
        input_snapshot={"profile": _profile(), "context": {}},
        context_snapshot={"profile": _profile(), "context": {}},
    )
    event = WorkflowOutbox(
        aggregate_type="skill_run",
        aggregate_id=run.id,
        event_type="skill.run.requested",
        payload_json={"skill_run_id": run.id},
        status="PUBLISHED",
        retry_count=0,
        created_at=datetime.utcnow(),
    )
    skill_db.add(event)
    await skill_db.flush()

    gateway = StubGateway(_report_text())
    monkeypatch.setattr(skill_runtime, "DeepSeekGateway", lambda: gateway)
    monkeypatch.setattr(
        workflow_tasks, "AsyncSessionLocal", lambda: SessionContext(skill_db)
    )
    first = await workflow_tasks._consume_outbox_event(event.id)
    repeated = await workflow_tasks._consume_outbox_event(event.id)

    assert first["status"] == "completed"
    assert repeated["status"] == "completed"
    assert gateway.calls == 1


@pytest.mark.asyncio
async def test_case_skill_run_requires_assigned_consultant(skill_db):
    from app.application.skill_runtime import queue_case_step_skill_run

    version = await ensure_default_skill_version(skill_db)
    report_case = ReportCase(
        id=81,
        user_id=19,
        service_request_id=77,
        status="ACTIVE",
        application_snapshot={"profile": _profile(), "context": {}},
        application_submitted_at=datetime.utcnow(),
        workflow_instance_id=202,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    step = StepTask(
        id=303,
        workflow_instance_id=202,
        step_key="S5",
        sequence_no=5,
        executor="HYBRID",
        status="READY",
        required_capability="consultant",
        assignee_id=7,
        activation_no=1,
        config_snapshot={"skill_version_id": version.id},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    skill_db.add_all([report_case, step])
    await skill_db.flush()
    assigned_db = CaseAccessSession(
        skill_db.session,
        SimpleNamespace(assigned_consultant_id=7, status="accepted"),
    )
    assigned = await queue_case_step_skill_run(
        assigned_db,
        case_id=report_case.id,
        step_key="S5",
        actor=SimpleNamespace(id=7, role="consultant"),
        idempotency_key="case-81-step-s5",
        runtime_instruction=None,
    )
    assert assigned[0].report_case_id == 81

    unassigned_db = CaseAccessSession(
        skill_db.session,
        SimpleNamespace(assigned_consultant_id=8, status="accepted"),
    )
    with pytest.raises(ValueError, match="report_case_forbidden"):
        await queue_case_step_skill_run(
            unassigned_db,
            case_id=report_case.id,
            step_key="S5",
            actor=SimpleNamespace(id=7, role="consultant"),
            idempotency_key="case-81-step-s5-unassigned",
            runtime_instruction=None,
        )


@pytest.mark.asyncio
async def test_analysis_workflow_pins_hybrid_skills_to_s1_through_s4(skill_db):
    from app.application.report_cases import ensure_default_workflow_version
    from app.application.skill_runtime import (
        ensure_analysis_workflow_version,
        ensure_skill_workflow_version,
    )

    await ensure_default_workflow_version(skill_db)
    await ensure_skill_workflow_version(skill_db)
    first = await ensure_analysis_workflow_version(skill_db)
    second = await ensure_analysis_workflow_version(skill_db)

    assert first.id == second.id
    steps = {item["step_key"]: item for item in first.definition_json["steps"]}
    for step_key in ("S1", "S2", "S3", "S4"):
        assert steps[step_key]["executor"] == "HYBRID"
        assert steps[step_key]["config"]["skill_key"].startswith("report.s")
        assert steps[step_key]["config"]["skill_version_id"]
    assert steps["S5"]["executor"] == "HYBRID"
    assert steps["S6"]["executor"] == "HUMAN"


@pytest.mark.asyncio
async def test_analysis_draft_is_assignment_checked_and_candidates_keep_run_provenance(skill_db):
    from app.application.report_analysis import (
        apply_analysis_finding_candidate,
        apply_analysis_fragment_candidate,
        queue_case_analysis_draft,
    )

    now = datetime.utcnow()
    report_case = ReportCase(
        id=84,
        user_id=19,
        service_request_id=77,
        status="ACTIVE",
        application_snapshot={
            "profile": _profile(),
            "context": {"current_challenge": "评估工作方向"},
        },
        application_submitted_at=now,
        workflow_instance_id=204,
        created_at=now,
        updated_at=now,
    )
    previous = StepTask(
        id=304,
        workflow_instance_id=204,
        step_key="S1",
        sequence_no=1,
        executor="HUMAN",
        status="COMPLETED",
        required_capability="consultant",
        assignee_id=7,
        activation_no=1,
        config_snapshot={},
        created_at=now,
        updated_at=now,
    )
    current = StepTask(
        id=305,
        workflow_instance_id=204,
        step_key="S2",
        sequence_no=2,
        executor="HUMAN",
        status="IN_REVIEW",
        required_capability="consultant",
        assignee_id=7,
        activation_no=1,
        config_snapshot={},
        created_at=now,
        updated_at=now,
        started_at=now,
    )
    evidence = CaseEvidenceItem(
        id=405,
        report_case_id=84,
        evidence_key="input.context.current_challenge",
        source_type="USER_PROVIDED",
        source_ref="application_snapshot.context.current_challenge",
        value_json="评估工作方向",
        status="ACTIVE",
        created_by=None,
        created_at=now,
    )
    upstream = FindingRevision(
        id=406,
        report_case_id=84,
        finding_key="foundation.balance",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        kind="FINDING",
        semantic_role="CORE_STRUCTURE",
        claim="用户重视可预期的工作节奏。",
        confidence="MEDIUM",
        importance="HIGH",
        reportability="RECOMMENDED",
        status="CONFIRMED",
        evidence_refs=[evidence.evidence_key],
        relation_refs=[],
        structured_data_json={},
        edit_kind="SEMANTIC",
        is_current=True,
        owner_step_task_id=previous.id,
        source_skill_run_id=None,
        created_by=None,
        created_at=now,
    )
    skill_db.add_all([report_case, previous, current, evidence, upstream])
    await skill_db.flush()
    actor = SimpleNamespace(id=7, role="consultant")
    assigned_db = CaseAccessSession(
        skill_db.session,
        SimpleNamespace(assigned_consultant_id=7, status="accepted"),
    )

    run, created = await queue_case_analysis_draft(
        assigned_db,
        case_id=84,
        step_key="S2",
        actor=actor,
        idempotency_key="case-84-s2-activation-1",
    )
    assert created is True
    assert run.target_type == "REPORT_ANALYSIS_DRAFT"
    assert run.step_task_id == current.id
    assert run.input_snapshot["analysis_context"]["upstream_confirmed_findings"][0]["finding_key"] == upstream.finding_key
    assert run.context_snapshot["analysis_activation_no"] == current.activation_no

    unassigned_db = CaseAccessSession(
        skill_db.session,
        SimpleNamespace(assigned_consultant_id=8, status="accepted"),
    )
    with pytest.raises(ValueError, match="report_case_forbidden"):
        await queue_case_analysis_draft(
            unassigned_db,
            case_id=84,
            step_key="S2",
            actor=actor,
            idempotency_key="case-84-s2-unassigned",
        )

    run.status = "COMPLETED"
    run.output_parsed = {
        "summary": "基于用户情境和已确认上游判断形成心理映射候选。",
        "findings": [
            {
                "finding_key": "s2.psychology.autonomy",
                "claim": "用户希望在边界清楚时保留自主空间。",
                "kind": "FINDING",
                "semantic_role": "MOTIVATION_PATTERN",
                "confidence": "MEDIUM",
                "importance": "HIGH",
                "reportability": "RECOMMENDED",
                "evidence_refs": [evidence.evidence_key],
                "relation_refs": [{"finding_key": upstream.finding_key, "relation": "MAPS_TO"}],
                "structured_data": {},
            }
        ],
        "analysis_fragments": [
            {
                "fragment_key": "analysis.psychology.persona",
                "title": "心理映射候选",
                "content": "在边界清楚时，用户更容易开展探索。",
                "finding_refs": ["s2.psychology.autonomy"],
                "evidence_refs": [evidence.evidence_key],
            }
        ],
        "risk_flags": [],
    }
    run.context_snapshot = {
        **run.context_snapshot,
        "analysis_activation_no": current.activation_no,
    }
    finding = await apply_analysis_finding_candidate(
        assigned_db,
        case_id=84,
        step_key="S2",
        run_id=run.id,
        finding_key="s2.psychology.autonomy",
        expected_revision_no=None,
        actor=actor,
    )
    assert finding.status == "PROPOSED"
    assert finding.source_skill_run_id == run.id
    assert finding.owner_step_task_id == current.id

    fragment = await apply_analysis_fragment_candidate(
        assigned_db,
        case_id=84,
        step_key="S2",
        run_id=run.id,
        fragment_key="analysis.psychology.persona",
        expected_revision_no=None,
        actor=actor,
    )
    assert fragment.status == "PROPOSED"
    assert fragment.source_skill_run_id == run.id
    assert fragment.source_snapshot["findings"][0]["finding_key"] == finding.finding_key

    current.activation_no = 2
    with pytest.raises(ValueError, match="report_analysis_run_activation_changed"):
        await apply_analysis_finding_candidate(
            assigned_db,
            case_id=84,
            step_key="S2",
            run_id=run.id,
            finding_key="s2.psychology.autonomy",
            expected_revision_no=finding.revision_no,
            actor=actor,
        )


@pytest.mark.asyncio
async def test_skill_management_routes_reject_consultants():
    from app.api.v1.skills import admin_router

    for route in admin_router.routes:
        role_dependency = next(
            dependency
            for dependency in route.dependant.dependencies
            if dependency.name in {"actor", "_actor"}
        )
        role_guard = role_dependency.call
        with pytest.raises(HTTPException) as error:
            await role_guard(current_user=SimpleNamespace(role="consultant"))
        assert error.value.status_code == 403


def _completed_example_source(version, *, run_id=901, case_id=81):
    return SkillRun(
        id=run_id,
        skill_version_id=version.id,
        report_case_id=case_id,
        target_type="REPORT_CASE_STEP",
        target_key="S1",
        run_type="INITIAL",
        status="COMPLETED",
        idempotency_key=f"example-source-{run_id}",
        input_snapshot={
            "profile": _profile(),
            "context": {"focus_topics": ["career"]},
        },
        context_snapshot={"profile": _profile(), "context": {}},
        selected_examples=[],
        selected_knowledge=[],
        model_trace={},
        retry_count=0,
        created_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_skill_examples_require_redaction_and_publish_as_immutable_versions(skill_db):
    version = await ensure_default_skill_version(skill_db)
    source_run = _completed_example_source(version)
    skill_db.add(source_run)
    await skill_db.flush()
    candidate = await create_example_candidate(
        skill_db,
        report_case_id=81,
        skill_run=source_run,
        example_type="POSITIVE",
        scenario_tags=["career", "职业发展"],
        teaching_points=["林女士先用小步尝试收集信息。"],
        expected_output={"summary": "林女士 13812345678，1992-06-18"},
        created_by=7,
    )

    assert candidate.status == "CANDIDATE"
    assert candidate.input_context["profile"].get("name") is None
    assert "林女士" not in candidate.expected_output["summary"]
    assert "13812345678" not in candidate.expected_output["summary"]
    assert "1992-06-18" not in candidate.expected_output["summary"]
    assert await retrieve_skill_examples(
        skill_db,
        skill_key=version.skill_key,
        target_key=None,
        context={"focus_topics": ["career"]},
    ) == []

    with pytest.raises(ValueError, match="skill_example_deidentification_required"):
        await publish_skill_example(skill_db, candidate.id, reviewed_by=1)

    reviewed = await update_example_redaction(
        skill_db,
        example_id=candidate.id,
        target_fragment_key=None,
        scenario_tags=["career", "职业发展"],
        applicability_json={"focus_topics": ["career"]},
        input_context={"context": {"focus_topics": ["career"]}},
        expected_output={"summary": "使用小步尝试而非立即做出决定。"},
        teaching_points=["把建议写成可执行的小行动。"],
        anti_patterns=["保证某个确定结果"],
        quality_score=0.92,
        confirmed_deidentified=True,
    )
    published = await publish_skill_example(
        skill_db, reviewed.id, reviewed_by=1
    )
    assert published.status == "PUBLISHED"
    selected = await retrieve_skill_examples(
        skill_db,
        skill_key=version.skill_key,
        target_key=None,
        context={"focus_topics": ["career"]},
    )
    assert selected[0]["example_id"] == published.id
    assert selected[0]["version_no"] == 1
    assert selected[0]["retrieval_policy"]
    assert "scenario_tag_match" in selected[0]["selection_reasons"]
    await skill_db.commit()
    assert await retrieve_skill_examples(
        skill_db,
        skill_key=version.skill_key,
        target_key=None,
        context={"focus_topics": ["health"]},
    ) == []

    with pytest.raises(ValueError, match="skill_example_immutable"):
        published.teaching_points = ["attempt to edit published content"]
        await skill_db.flush()
    await skill_db.rollback()

    revision = await create_example_revision(
        skill_db, published.id, created_by=1
    )
    assert revision.version_no == 2
    assert revision.status == "CANDIDATE"
    assert revision.deidentified is False
    revised = await update_example_redaction(
        skill_db,
        example_id=revision.id,
        target_fragment_key=None,
        scenario_tags=["career"],
        applicability_json={},
        input_context={"context": {"focus_topics": ["career"]}},
        expected_output={"summary": "先试验，再整理信息。"},
        teaching_points=["先确定一个可观察的小行动。"],
        anti_patterns=[],
        quality_score=0.95,
        confirmed_deidentified=True,
    )
    await publish_skill_example(skill_db, revised.id, reviewed_by=1)
    assert published.status == "RETIRED"
    assert (await retrieve_skill_examples(
        skill_db,
        skill_key=version.skill_key,
        target_key=None,
        context={"focus_topics": ["career"]},
    ))[0]["version_no"] == 2


@pytest.mark.asyncio
async def test_skill_example_applicability_rejects_unsupported_or_invalid_conditions(skill_db):
    version = await ensure_default_skill_version(skill_db)
    source_run = _completed_example_source(version)
    skill_db.add(source_run)
    await skill_db.flush()
    candidate = await create_example_candidate(
        skill_db,
        report_case_id=81,
        skill_run=source_run,
        example_type="POSITIVE",
        scenario_tags=[],
        teaching_points=["Use a specific, practical suggestion."],
        expected_output={"summary": "A deidentified example."},
        created_by=7,
    )

    invalid_applicability = [
        ({"region": "north"}, "skill_example_applicability_key_unsupported"),
        ({"focus_topics": ["career", 3]}, "skill_example_applicability_value_invalid"),
        ({"decision_status": {"value": "yes"}}, "skill_example_applicability_value_invalid"),
        ({"usage_scenario": "  "}, "skill_example_applicability_value_invalid"),
    ]
    for applicability, error_code in invalid_applicability:
        with pytest.raises(ValueError, match=error_code):
            await update_example_redaction(
                skill_db,
                example_id=candidate.id,
                target_fragment_key=None,
                scenario_tags=[],
                applicability_json=applicability,
                input_context={"context": {}},
                expected_output={"summary": "A deidentified example."},
                teaching_points=["Use a specific, practical suggestion."],
                anti_patterns=[],
                quality_score=0.9,
                confirmed_deidentified=True,
            )
    assert candidate.applicability_json == {}


@pytest.mark.asyncio
async def test_dynamic_examples_are_snapshotted_and_given_style_only_prompt_guidance(
    skill_db, monkeypatch
):
    from app.application import skill_runtime

    published = await ensure_default_skill_version(skill_db)
    source_run = _completed_example_source(published)
    skill_db.add(source_run)
    await skill_db.flush()
    candidate = await create_example_candidate(
        skill_db,
        report_case_id=81,
        skill_run=source_run,
        example_type="POSITIVE",
        scenario_tags=["career"],
        teaching_points=["用审慎语气描述建议。"],
        expected_output={"summary": "一个脱敏后的写作示例。"},
        created_by=7,
    )
    await update_example_redaction(
        skill_db,
        example_id=candidate.id,
        target_fragment_key=None,
        scenario_tags=["career"],
        applicability_json={},
        input_context={"context": {"focus_topics": ["career"]}},
        expected_output={"summary": "一个脱敏后的写作示例。"},
        teaching_points=["用审慎语气描述建议。"],
        anti_patterns=[],
        quality_score=0.9,
        confirmed_deidentified=True,
    )
    await publish_skill_example(skill_db, candidate.id, reviewed_by=1)

    specification = default_skill_specification()
    specification["example_policy"] = {"enabled": True, "max_examples": 2}
    draft = await create_skill_draft(
        skill_db,
        skill_key=published.skill_key,
        name=published.name,
        category="AUTHORING",
        specification=specification,
        created_by=1,
    )
    run, _created = await skill_runtime.queue_debug_skill_run(
        skill_db,
        version_id=draft.id,
        idempotency_key="debug-run-with-example",
        input_data={
            "profile": _profile(),
            "context": {"focus_topics": ["career"]},
        },
        runtime_instruction=None,
    )
    assert run.selected_examples[0]["example_id"] == candidate.id
    assert run.selected_examples[0]["version_no"] == 1
    assert run.input_snapshot["few_shot_examples"][0]["teaching_points"] == [
        "用审慎语气描述建议。"
    ]

    gateway = StubGateway(_report_text())
    monkeypatch.setattr(skill_runtime, "DeepSeekGateway", lambda: gateway)
    completed = await skill_runtime.execute_skill_run_record(skill_db, run.id)
    assert completed.status == "COMPLETED"
    assert "已审核的脱敏示例" in gateway.last_request[0]
    assert "不得复制示例中的人物事实" in gateway.last_request[0]
    assert completed.model_trace["selected_examples"][0]["example_id"] == candidate.id


@pytest.mark.asyncio
async def test_regression_batches_persist_checks_and_gate_skill_publish(skill_db):
    from app.application.skill_evaluation import (
        ensure_evaluation_passed_before_publish,
        get_evaluation_batch,
        start_evaluation_batch,
    )

    version = await ensure_default_validator_skill_version(skill_db)
    with pytest.raises(ValueError, match="skill_evaluation_required"):
        await ensure_evaluation_passed_before_publish(skill_db, version.id)

    batch = await start_evaluation_batch(skill_db, version_id=version.id)
    assert batch["total"] == 1
    assert batch["completed"] == 0
    run = await skill_db.get(SkillRun, batch["runs"][0]["run_id"])
    assert run.target_type == "REGRESSION"
    assert run.context_snapshot["evaluation"]["dataset_version"]
    assert run.context_snapshot["evaluation"]["specification_sha256"]
    with pytest.raises(ValueError, match="skill_evaluation_incomplete"):
        await ensure_evaluation_passed_before_publish(skill_db, version.id)

    run.status = "COMPLETED"
    run.output_parsed = {"issues": []}
    run.context_snapshot = {
        **run.context_snapshot,
        "evaluation": {
            **run.context_snapshot["evaluation"],
            "result": {"score": 0.0, "passed": False, "checks": []},
        },
    }
    await skill_db.flush()
    failed_batch = await get_evaluation_batch(skill_db, batch["batch_id"])
    assert failed_batch["failed"] == 0
    assert failed_batch["passed"] == 0
    assert failed_batch["pass_rate"] == 0.0
    with pytest.raises(ValueError, match="skill_evaluation_failed"):
        await ensure_evaluation_passed_before_publish(skill_db, version.id)

    run.context_snapshot = {
        **run.context_snapshot,
        "evaluation": {
            **run.context_snapshot["evaluation"],
            "result": {"score": 1.0, "passed": True, "checks": []},
        },
    }
    await skill_db.flush()
    await ensure_evaluation_passed_before_publish(skill_db, version.id)


@pytest.mark.asyncio
async def test_builtin_validator_update_keeps_unpublished_skill_studio_draft(skill_db):
    from app.domains.skills.definitions import default_validator_skill_specification

    published = await ensure_default_validator_skill_version(skill_db)
    previous_specification = {
        **published.specification_json,
        "instructions": {
            **published.specification_json["instructions"],
            "objective": "Previous validator instructions.",
        },
    }
    published.specification_json = previous_specification
    await skill_db.flush()

    draft_specification = default_validator_skill_specification()
    draft = await create_skill_draft(
        skill_db,
        skill_key="report.final_validator",
        name=draft_specification["identity"]["name"],
        category="VALIDATOR",
        specification=draft_specification,
        created_by=7,
    )
    assert draft.version == 2

    updated = await ensure_default_validator_skill_version(skill_db)

    assert updated.version == 3
    assert updated.status == "PUBLISHED"
    assert draft.status == "DRAFT"
    assert draft.specification_json == draft_specification


@pytest.mark.asyncio
async def test_regression_batch_executes_through_skill_runtime_and_persists_result(skill_db):
    from app.application import skill_runtime
    from app.application.skill_evaluation import get_evaluation_batch, start_evaluation_batch

    version = await ensure_default_validator_skill_version(skill_db)
    batch = await start_evaluation_batch(skill_db, version_id=version.id)
    run_id = batch["runs"][0]["run_id"]
    gateway = StubGateway(
        '{"issues":[{"issue_type":"PREDICTIVE_CERTAINTY","severity":"BLOCK",'
        '"message":"需要移除确定性预测。","evidence":"你一定会在今年获得晋升。",'
        '"suggestion":"改为说明当前证据及不确定性。",'
        '"target_fragment_key":"report.direction"}]}'
    )

    completed = await skill_runtime.execute_skill_run_record(
        skill_db, run_id, gateway=gateway
    )
    result = completed.context_snapshot["evaluation"]["result"]
    refreshed_batch = await get_evaluation_batch(skill_db, batch["batch_id"])

    assert gateway.calls == 1
    assert completed.status == "COMPLETED"
    assert result["passed"] is True
    assert all(check["passed"] for check in result["checks"])
    assert refreshed_batch["pass_rate"] == 1.0
    selected = refreshed_batch["runs"][0]["selected_examples"]
    assert [item["example_key"] for item in selected] == ["review-reader-copy-v1"]
    assert selected[0]["example_snapshot"]["input_context"]["report_fragments"]


def test_regression_expectations_score_schema_paths_and_finding_boundaries():
    passing = evaluate_regression_output(
        {
            "status": "READY_FOR_REVIEW",
            "used_findings": ["finding.small-step"],
        },
        {
            "required_fields": ["status", "used_findings"],
            "allowed_finding_refs": ["finding.small-step"],
            "minimum_score": 1.0,
        },
    )
    failing = evaluate_regression_output(
        {"status": "READY_FOR_REVIEW", "used_findings": ["finding.new"]},
        {
            "required_fields": ["status", "content"],
            "allowed_finding_refs": ["finding.small-step"],
            "minimum_score": 1.0,
        },
    )
    assert passing["passed"] is True
    assert failing["passed"] is False
    assert any(not check["passed"] for check in failing["checks"])
