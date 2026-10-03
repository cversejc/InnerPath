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
from app.domains.content.report_content_plan import (
    build_report_content_plan,
    validate_report_content_plan,
)
from app.domains.skills.definitions import default_narrative_skill_specifications
from app.domains.skills.models import AISkillVersion, SkillRun, SkillExample
from app.domains.skills.runtime import (
    ModelCompletion,
    SkillExecutionError,
    _authoring_prompts,
    execute_skill,
)
from app.domains.reports.models import ReportTask
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowOutbox,
    WorkflowVersion,
)


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
        SkillExample.__table__,
        FindingRevision.__table__,
        CaseEvidenceItem.__table__,
        ContentFragmentRevision.__table__,
        NarrativePlan.__table__,
        WorkflowVersion.__table__,
        WorkflowInstance.__table__,
        StepTask.__table__,
        WorkflowOutbox.__table__,
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


def test_narrative_prompt_includes_required_candidate_item_contract():
    specification = default_narrative_skill_specifications()[0]
    required = specification["output_contract"]["properties"]["candidates"]["items"]["required"]

    assert "candidate_key" in required
    assert "supporting_findings" in required
    assert "priority_blocks" in required
    system_prompt, _user_prompt = _authoring_prompts({}, specification, None)
    assert '"candidate_key": {' in system_prompt


def test_fragment_authoring_contract_lists_runtime_status_values():
    specification = default_narrative_skill_specifications()[1]
    status_schema = specification["output_contract"]["properties"]["status"]

    assert status_schema["enum"] == [
        "READY_FOR_REVIEW",
        "MISSING_SEMANTIC_SUPPORT",
    ]
    system_prompt, _user_prompt = _authoring_prompts({}, specification, None)
    assert "READY_FOR_REVIEW" in system_prompt
    assert "MISSING_SEMANTIC_SUPPORT" in system_prompt


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
        "fragment_allocation": {
            "fragment_key": "report.identity.core",
            "finding_refs": ["finding.core"],
            "analysis_refs": [],
            "evidence_refs": [],
            "action_refs": [],
            "must_cover": ["已确认核心判断"],
            "finding_roles": {"finding.core": "INTRODUCE"},
            "new_information_role": "INTRODUCE",
        },
        "continuity": {},  # First allocated fragment has no preceding prose.
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


def test_report_content_plan_allocates_confirmed_semantics_and_reports_gaps():
    semantic_model = {
        "findings": [
            {
                "finding_key": "finding.identity",
                "semantic_role": "IDENTITY",
                "claim": "Identity source",
                "importance": "HIGH",
                "confidence": "HIGH",
                "reportability": "MUST_INCLUDE",
                "evidence_refs": ["evidence.identity"],
                "structured_data": {},
            },
            {
                "finding_key": "finding.hidden",
                "semantic_role": "HIDDEN_TENSION",
                "claim": "Hidden source",
                "importance": "MEDIUM",
                "confidence": "MEDIUM",
                "reportability": "RECOMMENDED",
                "evidence_refs": [],
                "structured_data": {},
            },
            {
                "finding_key": "finding.block",
                "semantic_role": "CHALLENGE",
                "claim": "Block source",
                "importance": "HIGH",
                "confidence": "HIGH",
                "reportability": "MUST_INCLUDE",
                "evidence_refs": [],
                "structured_data": {},
            },
            {
                "finding_key": "finding.action",
                "semantic_role": "ACTION",
                "claim": "Action source",
                "importance": "MEDIUM",
                "confidence": "HIGH",
                "reportability": "RECOMMENDED",
                "evidence_refs": [],
                "structured_data": {},
            },
            {
                "finding_key": "finding.direction",
                "semantic_role": "SELF_DIRECTION",
                "claim": "Direction source",
                "importance": "MEDIUM",
                "confidence": "HIGH",
                "reportability": "RECOMMENDED",
                "evidence_refs": [],
                "structured_data": {},
            },
        ],
        "analysis_fragments": [
            {
                "fragment_key": "analysis.identity.context",
                "source_snapshot": {
                    "findings": [{"finding_key": "finding.identity"}],
                    "fragments": [],
                    "evidence": [],
                },
            }
        ],
        "evidence": [],
    }
    narrative_plan = {
        "must_include_findings": ["finding.identity", "finding.block"],
        "self_direction": "finding.direction",
        "priority_blocks": [
            {"block_key": "block.main", "title": "Main block", "finding_refs": ["finding.block"]}
        ],
    }

    plan = build_report_content_plan(semantic_model, narrative_plan)
    issues = validate_report_content_plan(plan, semantic_model, narrative_plan)
    growth = next(
        item
        for item in plan["fragments"]
        if item["fragment_key"] == "report.direction.growth_experiments"
    )

    assert plan["status"] == "READY"
    assert 6 <= len(plan["fragments"]) <= 18
    assert not issues
    assert growth["finding_refs"] == [
        "finding.block",
        "finding.direction",
        "finding.action",
    ]
    assert growth["action_refs"] == ["finding.action"]
    assert plan["finding_usage"]["finding.block"]["used_in"]
    identity = next(
        item
        for item in plan["fragments"]
        if item["fragment_key"] == "report.identity.outer_self"
    )
    assert identity["analysis_refs"] == ["analysis.identity.context"]
    assert plan["analysis_coverage"]["analysis.identity.context"] == [
        "report.identity.outer_self"
    ]

    missing_action = {
        **semantic_model,
        "findings": [
            item for item in semantic_model["findings"] if item["finding_key"] != "finding.action"
        ],
    }
    blocked = build_report_content_plan(missing_action, narrative_plan)
    assert blocked["status"] == "BLOCKED"
    assert any(item["type"] == "MISSING_SEMANTIC_SUPPORT" for item in blocked["gaps"])


def test_report_content_plan_recognizes_chinese_semantic_roles():
    semantic_model = {
        "findings": [
            {
                "finding_key": "finding.identity",
                "semantic_role": "IDENTITY",
                "claim": "Identity source",
                "importance": "HIGH",
                "confidence": "HIGH",
                "reportability": "MUST_INCLUDE",
                "evidence_refs": ["evidence.identity"],
                "structured_data": {},
            },
            {
                "finding_key": "finding.hidden",
                "semantic_role": "HIDDEN_TENSION",
                "claim": "Hidden source",
                "importance": "MEDIUM",
                "confidence": "MEDIUM",
                "reportability": "RECOMMENDED",
                "evidence_refs": [],
                "structured_data": {},
            },
            {
                "finding_key": "finding.block",
                "semantic_role": "中心张力候选",
                "claim": "Block source",
                "importance": "HIGH",
                "confidence": "HIGH",
                "reportability": "MUST_INCLUDE",
                "evidence_refs": [],
                "structured_data": {},
            },
            {
                "finding_key": "finding.action",
                "semantic_role": "低风险行动候选",
                "claim": "Action source",
                "importance": "MEDIUM",
                "confidence": "HIGH",
                "reportability": "RECOMMENDED",
                "evidence_refs": [],
                "structured_data": {},
            },
            {
                "finding_key": "finding.direction",
                "semantic_role": "自我方向候选",
                "claim": "Direction source",
                "importance": "MEDIUM",
                "confidence": "HIGH",
                "reportability": "RECOMMENDED",
                "evidence_refs": [],
                "structured_data": {},
            },
        ],
        "analysis_fragments": [
            {
                "fragment_key": "analysis.identity.context",
                "source_snapshot": {
                    "findings": [{"finding_key": "finding.identity"}],
                    "fragments": [],
                    "evidence": [],
                },
            }
        ],
        "evidence": [],
    }
    narrative_plan = {
        "must_include_findings": ["finding.identity", "finding.block"],
        "self_direction": "finding.direction",
        "priority_blocks": [
            {
                "block_key": "block.main",
                "title": "Main block",
                "finding_refs": ["finding.block"],
            }
        ],
    }

    plan = build_report_content_plan(semantic_model, narrative_plan)
    issues = validate_report_content_plan(plan, semantic_model, narrative_plan)
    growth = next(
        item
        for item in plan["fragments"]
        if item["fragment_key"] == "report.direction.growth_experiments"
    )

    assert plan["status"] == "READY"
    assert not issues
    assert growth["finding_refs"] == [
        "finding.block",
        "finding.direction",
        "finding.action",
    ]
    assert growth["action_refs"] == ["finding.action"]


@pytest.mark.asyncio
async def test_report_analysis_gate_requires_completed_s1_through_s4(narrative_db):
    from app.application.report_generation import validate_report_analysis_steps

    db, case_id, _run_id, _finding_id = narrative_db
    now = datetime.utcnow()
    workflow = WorkflowVersion(
        workflow_key="test.workflow",
        name="Test workflow",
        version=1,
        status="PUBLISHED",
        definition_json={"steps": []},
        created_at=now,
        published_at=now,
    )
    db.add(workflow)
    await db.flush()
    instance = WorkflowInstance(
        report_case_id=case_id,
        workflow_version_id=workflow.id,
        status="RUNNING",
        created_at=now,
        updated_at=now,
        started_at=now,
    )
    db.add(instance)
    await db.flush()
    case = await db.get(ReportCase, case_id)
    case.workflow_instance_id = instance.id
    steps = [
        StepTask(
            workflow_instance_id=instance.id,
            step_key=f"S{sequence_no}",
            sequence_no=sequence_no,
            executor="HUMAN",
            status="COMPLETED" if sequence_no < 4 else "IN_REVIEW",
            required_capability="consultant",
            activation_no=1,
            config_snapshot={"completion_policy": "MANUAL"},
            created_at=now,
            updated_at=now,
        )
        for sequence_no in range(1, 5)
    ]
    for step in steps:
        db.add(step)
    await db.flush()

    with pytest.raises(ValueError, match="report_analysis_steps_incomplete"):
        await validate_report_analysis_steps(db, case_id)

    steps[-1].status = "COMPLETED"
    analysis = ContentFragmentRevision(
        report_case_id=case_id,
        fragment_key="analysis.pending",
        revision_no=1,
        semantic_revision=1,
        content_revision=1,
        fragment_type="ANALYSIS",
        title="Pending analysis",
        content="Needs review.",
        status="PROPOSED",
        source_snapshot={},
        edit_kind="SEMANTIC",
        is_current=True,
        created_at=now,
    )
    db.add(analysis)
    await db.flush()

    with pytest.raises(ValueError, match="report_analysis_fragments_incomplete"):
        await validate_report_analysis_steps(db, case_id)

    analysis.status = "CONFIRMED"
    await db.flush()
    await validate_report_analysis_steps(db, case_id)


@pytest.mark.asyncio
async def test_report_generation_runs_fragments_in_order_with_continuity_and_gate(
    narrative_db,
):
    from app.application.report_generation import (
        advance_case_report_generation,
        start_case_report_coherence_check,
        start_case_report_generation,
        validate_report_authoring_completion,
    )
    from app.application.skill_runtime import execute_skill_run_record

    db, case_id, candidate_run_id, _finding_id = narrative_db
    case = await db.get(ReportCase, case_id)
    now = datetime.utcnow()
    case.application_snapshot = {
        "profile": {"name": "Test"},
        "context": {"focus_topics": ["work"]},
    }

    finding_specs = [
        ("finding.identity", "IDENTITY"),
        ("finding.hidden", "HIDDEN_TENSION"),
        ("finding.block.one", "CHALLENGE"),
        ("finding.block.two", "DEFENSE"),
        ("finding.action", "ACTION"),
        ("finding.direction", "SELF_DIRECTION"),
    ]
    for finding_key, role in finding_specs:
        db.add(
            FindingRevision(
                report_case_id=case_id,
                finding_key=finding_key,
                revision_no=1,
                semantic_revision=1,
                content_revision=1,
                kind="FINDING",
                semantic_role=role,
                claim=f"Confirmed source for {finding_key}.",
                confidence="HIGH",
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
        )
    db.add(
        ContentFragmentRevision(
            report_case_id=case_id,
            fragment_key="analysis.identity.context",
            revision_no=1,
            semantic_revision=1,
            content_revision=1,
            fragment_type="ANALYSIS",
            title="Identity analysis",
            content="Confirmed analysis connected to the identity finding.",
            status="CONFIRMED",
            source_snapshot={
                "findings": [
                    {
                        "finding_key": "finding.identity",
                        "revision_no": 1,
                        "semantic_revision": 1,
                    }
                ],
                "fragments": [],
                "evidence": [],
            },
            edit_kind="SEMANTIC",
            is_current=True,
            created_at=now,
        )
    )
    await db.flush()
    semantic_model = await load_case_semantic_model(db, case_id)
    supported = [item["finding_key"] for item in semantic_model["findings"]]
    candidate_run = await db.get(SkillRun, candidate_run_id)
    candidate_run.context_snapshot = {
        "semantic_source_snapshot": semantic_source_snapshot(semantic_model)
    }
    candidate_run.output_parsed = {
        "candidates": [
            {
                "candidate_key": "candidate_a",
                "theme": "Grounded report theme",
                "rationale": "The selected theme follows confirmed sources.",
                "supporting_findings": supported,
                "deemphasized_findings": [],
                "priority_blocks": [
                    {
                        "block_key": "block.one",
                        "title": "First block",
                        "finding_refs": ["finding.block.one"],
                    },
                    {
                        "block_key": "block.two",
                        "title": "Second block",
                        "finding_refs": ["finding.block.two"],
                    },
                ],
                "narrative_arc": [],
            }
        ]
    }

    workflow_version = WorkflowVersion(
        workflow_key="test.workflow",
        name="Test workflow",
        version=1,
        status="PUBLISHED",
        definition_json={"steps": []},
        created_at=now,
        published_at=now,
    )
    db.add(workflow_version)
    await db.flush()
    instance = WorkflowInstance(
        report_case_id=case_id,
        workflow_version_id=workflow_version.id,
        status="RUNNING",
        created_at=now,
        updated_at=now,
        started_at=now,
    )
    db.add(instance)
    await db.flush()
    case.workflow_instance_id = instance.id
    step = StepTask(
        workflow_instance_id=instance.id,
        step_key="S5",
        sequence_no=5,
        executor="HUMAN",
        status="IN_REVIEW",
        required_capability="consultant",
        activation_no=1,
        config_snapshot={"completion_policy": "MANUAL"},
        created_at=now,
        updated_at=now,
    )
    prior_steps = [
        StepTask(
            workflow_instance_id=instance.id,
            step_key=f"S{sequence_no}",
            sequence_no=sequence_no,
            executor="HUMAN",
            status="COMPLETED",
            required_capability="consultant",
            activation_no=1,
            config_snapshot={"completion_policy": "MANUAL"},
            created_at=now,
            updated_at=now,
        )
        for sequence_no in range(1, 5)
    ]
    for prior_step in prior_steps:
        db.add(prior_step)
    db.add(step)
    authoring_spec = default_narrative_skill_specifications()[1]
    db.add(
        AISkillVersion(
            skill_key=authoring_spec["identity"]["skill_key"],
            name=authoring_spec["identity"]["name"],
            category="AUTHORING",
            version=1,
            status="PUBLISHED",
            specification_json=authoring_spec,
            created_at=now,
            published_at=now,
        )
    )
    await db.flush()

    plan = await confirm_narrative_plan(
        db,
        report_case_id=case_id,
        skill_run_id=candidate_run_id,
        candidate_key="candidate_a",
        overrides={
            "must_include_findings": supported,
            "self_direction": "finding.direction",
        },
        actor_id=12,
    )
    assert plan.plan_json["content_plan"]["status"] == "READY"
    allocations = plan.plan_json["content_plan"]["fragments"]
    assert any(
        "analysis.identity.context" in allocation["analysis_refs"]
        for allocation in allocations
    )
    admin = SimpleNamespace(id=12, role="admin")
    await start_case_report_generation(
        db,
        case_id=case_id,
        actor=admin,
        idempotency_key="report-generation-test",
    )

    class AllocationGateway:
        async def complete(self, *, user_prompt, **_kwargs):
            context = json.loads(user_prompt)["context"]
            allocation = context["fragment_allocation"]
            response = {
                "status": "READY_FOR_REVIEW",
                "title": allocation["fragment_key"].rsplit(".", 1)[-1],
                "content": f"Grounded content for {allocation['fragment_key']}.",
                "used_findings": allocation["finding_refs"],
                "used_analysis_fragments": allocation["analysis_refs"],
                "used_actions": allocation["action_refs"],
                "transition_hint": f"Carry forward {allocation['fragment_key']}.",
                "presentation_meta": {"key_points": [allocation["fragment_key"]]},
            }
            return ModelCompletion(
                content=json.dumps(response),
                trace={"provider": "test", "model": "allocation-stub"},
            )

    sequence = []
    coherence_run_count = 0
    chapter_check_runs = []
    chapter_blocked_once = False
    while True:
        generation = plan.plan_json["generation"]
        if generation["status"] == "CHAPTER_COHERENCE_BLOCKED":
            with pytest.raises(ValueError, match="report_authoring_not_ready"):
                await validate_report_authoring_completion(db, case_id)
            from app.domains.content.fragments import create_content_fragment_revision

            target_key = generation["issues"][0]["target_fragment"]
            current_fragment = await db.scalar(
                select(ContentFragmentRevision).where(
                    ContentFragmentRevision.report_case_id == case_id,
                    ContentFragmentRevision.fragment_key == target_key,
                    ContentFragmentRevision.is_current.is_(True),
                )
            )
            revised_fragment = await create_content_fragment_revision(
                db,
                report_case_id=case_id,
                fragment_key=target_key,
                content=f"{current_fragment.content}\nRevised after chapter feedback.",
                fragment_type="REPORT",
                edit_kind="STYLE",
            )
            assert revised_fragment.revision_no == current_fragment.revision_no + 1
            retry_run = await start_case_report_coherence_check(
                db,
                case_id=case_id,
                actor=admin,
                idempotency_key="chapter-coherence-retry",
            )
            assert retry_run.target_type == "REPORT_CHAPTER_COHERENCE"
            target_snapshot = next(
                item
                for item in retry_run.input_snapshot["context"]["qa_input"][
                    "report_fragments"
                ]
                if item["fragment_key"] == target_key
            )
            assert target_snapshot["revision_no"] == revised_fragment.revision_no
            completed = await execute_skill_run_record(
                db, retry_run.id, gateway=FixedGateway({"issues": []})
            )
            assert completed.status == "COMPLETED"
            plan = await advance_case_report_generation(db, retry_run.id)
            chapter_check_runs.append(retry_run.target_key)
            continue
        if generation["status"] in {"CHAPTER_COHERENCE_CHECK", "COHERENCE_CHECK"}:
            run = await db.get(SkillRun, generation["active_run_id"])
            if run.target_type == "REPORT_CHAPTER_COHERENCE":
                chapter_check_runs.append(run.target_key)
                assert run.input_snapshot["context"]["qa_input"]["validation_scope"] == [
                    "chapter_coherence"
                ]
                assert {
                    next(
                        item["chapter"]
                        for item in allocations
                        if item["fragment_key"] == fragment["fragment_key"]
                    )
                    for fragment in run.input_snapshot["context"]["qa_input"][
                        "report_fragments"
                    ]
                } == {run.target_key.removeprefix("chapter:")}
                if not chapter_blocked_once:
                    first_fragment = next(
                        item["fragment_key"]
                        for item in allocations
                        if item["chapter"] == run.target_key.removeprefix("chapter:")
                    )
                    coherence_output = {
                        "issues": [
                            {
                                "issue_type": "CHAPTER_TRANSITION",
                                "severity": "BLOCK",
                                "message": "The chapter transition needs revision.",
                                "evidence": "The chapter does not establish its throughline.",
                                "suggestion": "Revise the target fragment before continuing.",
                                "target_fragment_key": first_fragment,
                            }
                        ]
                    }
                    chapter_blocked_once = True
                else:
                    coherence_output = {"issues": []}
            elif coherence_run_count == 0:
                coherence_output = {
                    "issues": [
                        {
                            "issue_type": "REPEATED_IDEA",
                            "severity": "BLOCK",
                            "message": "The same conclusion is explained twice.",
                            "evidence": "Two neighboring sections repeat it.",
                            "suggestion": "Rewrite the later section as a reference.",
                            "target_fragment_key": allocations[0]["fragment_key"],
                        }
                    ]
                }
            else:
                coherence_output = {"issues": []}
            completed = await execute_skill_run_record(
                db, run.id, gateway=FixedGateway(coherence_output)
            )
            assert completed.status == "COMPLETED"
            plan = await advance_case_report_generation(db, run.id)
            if run.target_type == "REPORT_COHERENCE":
                coherence_run_count += 1
            continue
        if generation["status"] != "IN_PROGRESS":
            break
        run_id = generation["active_run_id"]
        run = await db.get(SkillRun, run_id)
        allocation = run.input_snapshot["context"]["fragment_allocation"]
        projected_keys = {
            item["finding_key"]
            for item in run.input_snapshot["context"]["semantic_model"]["findings"]
        }
        assert projected_keys == set(allocation["finding_refs"])
        projected_analysis_keys = {
            item["fragment_key"]
            for item in run.input_snapshot["context"]["semantic_model"][
                "analysis_fragments"
            ]
        }
        assert projected_analysis_keys == set(allocation["analysis_refs"])
        if sequence:
            assert run.input_snapshot["context"]["continuity"]["previous_fragment_key"] == sequence[-1]
        sequence.append(allocation["fragment_key"])
        assert run.target_type == "REPORT_FRAGMENT"
        completed = await execute_skill_run_record(db, run.id, gateway=AllocationGateway())
        assert completed.status == "COMPLETED", (completed.error, completed.model_trace)
        plan = await advance_case_report_generation(db, run.id)

    assert sequence == [item["fragment_key"] for item in allocations]
    assert plan.plan_json["generation"]["status"] == "COHERENCE_BLOCKED"
    assert plan.plan_json["generation"]["issues"][0]["target_fragment"] == allocations[0]["fragment_key"]
    assert chapter_blocked_once
    assert set(plan.plan_json["generation"]["chapter_checks"]) == {
        item["chapter"] for item in allocations
    }
    assert all(
        result["status"] == "PASSED"
        for result in plan.plan_json["generation"]["chapter_checks"].values()
    )
    assert len(chapter_check_runs) == len(plan.plan_json["generation"]["chapter_checks"]) + 1
    with pytest.raises(ValueError, match="report_authoring_not_ready"):
        await validate_report_authoring_completion(db, case_id)

    coherence_run = await start_case_report_coherence_check(
        db,
        case_id=case_id,
        actor=admin,
        idempotency_key="report-coherence-retry",
    )
    completed = await execute_skill_run_record(
        db, coherence_run.id, gateway=FixedGateway({"issues": []})
    )
    assert completed.status == "COMPLETED"
    plan = await advance_case_report_generation(db, coherence_run.id)
    coherence_run_count += 1
    assert coherence_run_count == 2
    assert plan.plan_json["generation"]["status"] == "READY_FOR_REVIEW"
    assert plan.plan_json["generation"]["coherence"]["status"] == "PASSED"
    assert len(plan.plan_json["generation"]["completed_fragment_keys"]) == len(allocations)
    fragments = list(
        (await db.scalars(
            select(ContentFragmentRevision).where(
                ContentFragmentRevision.report_case_id == case_id,
                ContentFragmentRevision.fragment_type == "REPORT",
                ContentFragmentRevision.is_current.is_(True),
            )
        )).all()
    )
    assert len(fragments) == len(allocations)
    assert all(fragment.source_narrative_plan_id == plan.id for fragment in fragments)
    with pytest.raises(ValueError, match="report_authoring_not_ready"):
        await validate_report_authoring_completion(db, case_id)
    for fragment in fragments:
        fragment.status = "CONFIRMED"
    await db.flush()
    await validate_report_authoring_completion(db, case_id)
