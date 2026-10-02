from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.v1.report_cases import _workflow_error
from app.db.base import Base
from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
    NarrativePlan,
)
from app.domains.delivery import assembler
from app.domains.delivery.assembler import assemble_report_version
from app.domains.delivery.models import ReportVersion
from app.domains.quality.models import QAIssue
from app.domains.quality.service import resolve_qa_issue
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowVersion,
)


class SessionAdapter:
    def __init__(self, session):
        self.session = session

    def add(self, value):
        self.session.add(value)

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def get(self, model, identity):
        return self.session.get(model, identity)

    async def flush(self):
        self.session.flush()

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
        AISkillVersion.__table__,
        SkillRun.__table__,
        CaseEvidenceItem.__table__,
        FindingRevision.__table__,
        ContentFragmentRevision.__table__,
        NarrativePlan.__table__,
        QAIssue.__table__,
        ReportVersion.__table__,
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
async def test_assembled_report_version_captures_s6_attestation(
    quality_db, monkeypatch
):
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
    gate_result = {
        "final_gate_approved": True,
        "validator_run_id": 31,
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
        selected_skill_run_id=1,
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
            source_narrative_plan_id=plan.id,
            created_at=now,
        )
    )
    monkeypatch.setattr(
        assembler,
        "load_case_semantic_model",
        AsyncMock(return_value={"findings": [], "analysis_fragments": [], "evidence": []}),
    )

    version = await assemble_report_version(quality_db, case, actor_id=8)

    assert version.semantic_snapshot["final_gate"]["result_json"] == gate_result
    assert version.semantic_snapshot["final_gate"]["activation_no"] == 2


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
