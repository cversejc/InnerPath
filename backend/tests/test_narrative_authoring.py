import json
from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domains.content.dependencies import mark_dependents_stale
from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
    NarrativePlan,
)
from app.domains.content.fragments import create_content_fragment_revision
from app.domains.content.narrative import (
    confirm_narrative_plan,
    semantic_source_snapshot,
)
from app.domains.content.queries import load_case_semantic_model
from app.domains.skills.definitions import default_narrative_skill_specifications
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.runtime import (
    ModelCompletion,
    SkillExecutionError,
    execute_skill,
)
from app.domains.reports.models import ReportTask
from app.domains.workflow.models import ReportCase


class SyncSessionAdapter:
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

    async def refresh(self, value):
        self.session.refresh(value)

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

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
def narrative_db():
    tables = [
        ReportCase.__table__,
        AISkillVersion.__table__,
        SkillRun.__table__,
        FindingRevision.__table__,
        CaseEvidenceItem.__table__,
        ContentFragmentRevision.__table__,
        NarrativePlan.__table__,
    ]
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine, expire_on_commit=False) as session:
        db = SyncSessionAdapter(session)
        now = datetime.utcnow()
        case = ReportCase(
            user_id=1,
            status="ACTIVE",
            application_snapshot={},
            application_submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        skill = AISkillVersion(
            skill_key="report.narrative_plan",
            name="Narrative candidate test",
            category="AUTHORING",
            version=1,
            status="PUBLISHED",
            specification_json={},
            created_at=now,
        )
        session.add_all([case, skill])
        session.flush()
        finding = FindingRevision(
            report_case_id=case.id,
            finding_key="finding.core",
            revision_no=1,
            semantic_revision=1,
            content_revision=1,
            kind="FINDING",
            semantic_role="PATTERN",
            claim="A confirmed, bounded observation.",
            confidence="MEDIUM",
            importance="MEDIUM",
            reportability="RECOMMENDED",
            status="CONFIRMED",
            evidence_refs=[],
            relation_refs=[],
            structured_data_json={},
            edit_kind="SEMANTIC",
            is_current=True,
            created_at=now,
        )
        session.add(finding)
        session.flush()
        semantic_model = {
            "findings": [
                {
                    "finding_key": finding.finding_key,
                    "revision_no": finding.revision_no,
                    "semantic_revision": finding.semantic_revision,
                    "kind": finding.kind,
                    "semantic_role": finding.semantic_role,
                    "claim": finding.claim,
                    "confidence": finding.confidence,
                    "importance": finding.importance,
                    "reportability": finding.reportability,
                    "evidence_refs": [],
                    "structured_data": {},
                }
            ],
            "analysis_fragments": [],
            "evidence": [],
        }
        sources = semantic_source_snapshot(semantic_model)
        run = SkillRun(
            skill_version_id=skill.id,
            report_case_id=case.id,
            target_type="NARRATIVE_CANDIDATES",
            run_type="INITIAL",
            status="COMPLETED",
            idempotency_key="candidate-run-1",
            input_snapshot={},
            context_snapshot={"semantic_source_snapshot": sources},
            output_parsed={
                "candidates": [
                    {
                        "candidate_key": "candidate_a",
                        "theme": "A grounded theme",
                        "rationale": "A grounded reason.",
                        "supporting_findings": ["finding.core"],
                        "deemphasized_findings": [],
                        "priority_blocks": [],
                        "narrative_arc": [],
                    },
                    {
                        "candidate_key": "candidate_b",
                        "theme": "Another grounded theme",
                        "rationale": "A different grounded reason.",
                        "supporting_findings": ["finding.core"],
                        "deemphasized_findings": [],
                        "priority_blocks": [],
                        "narrative_arc": [],
                    },
                ]
            },
            selected_examples=[],
            selected_knowledge=[],
            model_trace={},
            retry_count=0,
            created_at=now,
        )
        session.add(run)
        session.flush()
        yield db, case.id, run.id, finding.id
    engine.dispose()


class FixedGateway:
    def __init__(self, response):
        self.response = response

    async def complete(self, **_kwargs):
        return ModelCompletion(
            content=json.dumps(self.response), trace={"provider": "test", "model": "stub"}
        )


@pytest.mark.asyncio
async def test_narrative_skill_rejects_unconfirmed_finding_references():
    specification = default_narrative_skill_specifications()[0]
    version = SimpleNamespace(
        id=7,
        skill_key=specification["identity"]["skill_key"],
        version=1,
        specification_json=specification,
    )
    output = {
        "candidates": [
            {
                "candidate_key": "candidate_a",
                "theme": "Theme one",
                "rationale": "Reason one",
                "supporting_findings": ["finding.unconfirmed"],
                "deemphasized_findings": [],
                "priority_blocks": [],
                "narrative_arc": [],
            },
            {
                "candidate_key": "candidate_b",
                "theme": "Theme two",
                "rationale": "Reason two",
                "supporting_findings": [],
                "deemphasized_findings": [],
                "priority_blocks": [],
                "narrative_arc": [],
            },
        ]
    }
    with pytest.raises(SkillExecutionError, match="narrative_candidate_unsupported_finding"):
        await execute_skill(
            skill_version=version,
            input_data={"context": {"semantic_model": {"findings": [], "analysis_fragments": [], "evidence": []}}},
            gateway=FixedGateway(output),
        )


@pytest.mark.asyncio
async def test_confirmed_plan_is_versioned_and_semantic_change_stales_report_fragments(
    narrative_db,
):
    db, case_id, run_id, finding_id = narrative_db
    semantic_model = await load_case_semantic_model(db, case_id)
    plan = await confirm_narrative_plan(
        db,
        report_case_id=case_id,
        skill_run_id=run_id,
        candidate_key="candidate_a",
        overrides={"must_include_findings": ["finding.core"]},
        actor_id=12,
    )
    assert plan.status == "CONFIRMED"
    assert plan.version_no == 1
    assert plan.source_snapshot == semantic_source_snapshot(semantic_model)

    fragment = ContentFragmentRevision(
        report_case_id=case_id,
        fragment_key="report.identity.core",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        fragment_type="REPORT",
        title="Core",
        content="Grounded report content.",
        status="CONFIRMED",
        source_snapshot={
            "findings": [{"finding_key": "finding.core", "revision_no": 1}],
            "fragments": [],
            "evidence": [],
        },
        edit_kind="SEMANTIC",
        is_current=True,
        source_narrative_plan_id=plan.id,
        created_at=datetime.utcnow(),
    )
    db.session.add(fragment)
    await db.flush()

    await mark_dependents_stale(
        db,
        report_case_id=case_id,
        origin_kind="finding",
        origin_key="finding.core",
        reason="semantic_dependency_changed:finding:core",
    )
    await db.refresh(plan)
    await db.refresh(fragment)
    assert plan.status == "STALE"
    assert fragment.status == "STALE"
    assert fragment.stale_reason == "SOURCE_CHANGED:finding:finding.core"


@pytest.mark.asyncio
async def test_narrative_plan_revision_stales_report_fragments_without_changing_findings(
    narrative_db,
):
    db, case_id, run_id, finding_id = narrative_db
    original_finding = await db.get(FindingRevision, finding_id)
    plan_v1 = await confirm_narrative_plan(
        db,
        report_case_id=case_id,
        skill_run_id=run_id,
        candidate_key="candidate_a",
        overrides={},
        actor_id=12,
    )
    fragment = await create_content_fragment_revision(
        db,
        report_case_id=case_id,
        fragment_key="report.identity.core",
        fragment_type="REPORT",
        title="核心模式",
        content="基于已确认判断写成的报告内容。",
        status="CONFIRMED",
        finding_refs=["finding.core"],
        source_narrative_plan_id=plan_v1.id,
    )

    plan_v2 = await confirm_narrative_plan(
        db,
        report_case_id=case_id,
        skill_run_id=run_id,
        candidate_key="candidate_b",
        overrides={"core_theme": "另一种叙事主线"},
        actor_id=12,
    )

    await db.refresh(plan_v1)
    await db.refresh(fragment)
    await db.refresh(original_finding)
    assert plan_v1.version_no == 1
    assert plan_v1.status == "SUPERSEDED"
    assert plan_v2.version_no == 2
    assert plan_v2.status == "CONFIRMED"
    assert fragment.status == "STALE"
    assert fragment.stale_reason == "NARRATIVE_CHANGED"
    assert original_finding.claim == "A confirmed, bounded observation."
    assert original_finding.semantic_revision == 1


@pytest.mark.asyncio
async def test_fragment_authoring_worker_saves_source_mapped_report_fragment(narrative_db):
    from app.application.skill_runtime import execute_skill_run_record

    db, case_id, candidate_run_id, _finding_id = narrative_db
    semantic_model = await load_case_semantic_model(db, case_id)
    plan = await confirm_narrative_plan(
        db,
        report_case_id=case_id,
        skill_run_id=candidate_run_id,
        candidate_key="candidate_a",
        overrides={"must_include_findings": ["finding.core"]},
        actor_id=12,
    )
    authoring_spec = default_narrative_skill_specifications()[1]
    authoring_skill = AISkillVersion(
        skill_key=authoring_spec["identity"]["skill_key"],
        name=authoring_spec["identity"]["name"],
        category="AUTHORING",
        version=1,
        status="PUBLISHED",
        specification_json=authoring_spec,
        created_at=datetime.utcnow(),
    )
    db.session.add(authoring_skill)
    await db.flush()
    context = {
        "semantic_model": semantic_model,
        "narrative_plan": plan.plan_json,
        "narrative_plan_id": plan.id,
        "fragment_request": {
            "fragment_key": "report.identity.core",
            "title": "核心模式",
        },
    }
    writer_run = SkillRun(
        skill_version_id=authoring_skill.id,
        report_case_id=case_id,
        target_type="REPORT_FRAGMENT",
        target_key="report.identity.core",
        run_type="INITIAL",
        status="PENDING",
        idempotency_key="writer-run-1",
        input_snapshot={"profile": {}, "context": context},
        context_snapshot={
            "profile": {},
            "context": context,
            "semantic_source_snapshot": plan.source_snapshot,
            "source_narrative_plan_id": plan.id,
        },
        selected_examples=[],
        selected_knowledge=[],
        model_trace={},
        retry_count=0,
        created_at=datetime.utcnow(),
    )
    db.session.add(writer_run)
    await db.flush()

    completed = await execute_skill_run_record(
        db,
        writer_run.id,
        gateway=FixedGateway(
            {
                "status": "READY_FOR_REVIEW",
                "title": "核心模式",
                "content": "这是由已确认判断支持的报告正文。",
                "used_findings": ["finding.core"],
                "used_analysis_fragments": [],
                "used_actions": [],
                "transition_hint": "继续查看下一节。",
                "presentation_meta": {},
            }
        ),
    )
    fragment = await db.scalar(
        select(ContentFragmentRevision).where(
            ContentFragmentRevision.report_case_id == case_id,
            ContentFragmentRevision.fragment_key == "report.identity.core",
            ContentFragmentRevision.is_current.is_(True),
        )
    )

    assert completed.status == "COMPLETED"
    assert fragment.status == "PROPOSED"
    assert fragment.source_narrative_plan_id == plan.id
    assert fragment.source_skill_run_id == writer_run.id
    assert fragment.source_snapshot["findings"] == [
        {"finding_key": "finding.core", "revision_no": 1, "semantic_revision": 1}
    ]
    assert fragment.source_snapshot["narrative_plan"]["version_no"] == plan.version_no
