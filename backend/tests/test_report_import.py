"""Consultant fast path: import a finished report and jump straight to S6.

The tests pin the workflow invariants that make the shortcut safe: S1-S5 are
marked completed without inventing analysis assets, S6 still runs the full
check while treating its findings as advice for one consultant authorization,
and the import stays idempotent and owner-aware.
"""
from datetime import datetime
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import ARRAY, JSON, create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.api.v1.report_cases import _workflow_error
from app.application.report_delivery import approve_case_final_gate, deliver_report_case
from app.application.report_import import (
    IMPORT_REVIEW_POLICY_VERSION,
    import_report_case,
)
from app.application.report_quality import queue_case_quality_run, quality_state
from app.db.base import Base
from app.domains.audit.models import AuditLog
from app.domains.content.models import (
    CaseEvidenceItem,
    ContentFragmentRevision,
    FindingRevision,
    NarrativePlan,
)
from app.domains.content.report_import import (
    ReportImportError,
    content_sha256,
    normalize_declared_hash,
    parse_report_content,
    render_import_markdown,
    verify_content_hash,
)
from app.domains.delivery.models import ReportVersion
from app.domains.quality.models import QAIssue
from app.domains.quality.scorecard import RUBRIC
from app.domains.reports.models import Report
from app.domains.review.models import NodeApproval, NodeReviewCommand, NodeReviewState
from app.domains.service_requests.models import ServiceRequest
from app.domains.skills.bindings import specification_digest
from app.domains.skills.models import AISkillVersion, SkillExample, SkillRun
from app.domains.skills.service import ensure_default_validator_skill_version
from app.domains.workflow.authorization import STEP_SPECIALTIES
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowOutbox,
    WorkflowVersion,
)
from app.services.llm import ChatCompletion
from tests.test_report_quality_delivery import SessionAdapter as _SessionAdapter
from tests.test_report_quality_delivery import StubGateway


class SessionAdapter(_SessionAdapter):
    """Adds the query and rollback surface the workflow service expects."""

    async def execute(self, statement):
        return self.session.execute(statement)

    async def rollback(self):
        self.session.rollback()


REPORT_TEXT = """# 你是谁

你重视自主空间，也愿意认真经营长期关系。你对承诺谨慎，但一旦确认就会投入。

# 卡在哪

你在稳定与自主之间反复权衡，担心一步走错就要从头再来，因此常常推迟决定。

# 往哪去

先用一个季度做小范围尝试，把可控的选择变成可验证的事实，再决定是否加码。
"""

# A report written the way consultants actually write: prose first, headings
# invented by the author, no fixed three-section contract.
FREEFORM_REPORT_TEXT = """林女士，1992 年生，目前在杭州生活。

她重视自主空间，也愿意认真经营长期关系；对承诺谨慎，一旦确认就会投入。

最近一年的困扰：在稳定与自主之间反复权衡，担心一步走错就要从头再来，因此常常推迟决定。

建议：先用一个季度做小范围尝试，把可控的选择变成可验证的事实，再决定是否加码。
"""

NORMALIZED_TEXT = """# 你是谁

林女士，1992 年生，目前在杭州生活。她重视自主空间，也愿意认真经营长期关系；对承诺谨慎，一旦确认就会投入。

# 卡在哪

最近一年的困扰：在稳定与自主之间反复权衡，担心一步走错就要从头再来，因此常常推迟决定。

# 往哪去

建议：先用一个季度做小范围尝试，把可控的选择变成可验证的事实，再决定是否加码。
"""


class StubNormalizationGateway:
    """Records normalization calls and replays a canned provider answer."""

    def __init__(self, content="", error=None):
        self.content = content
        self.error = error
        self.calls = []

    async def complete(self, *, system_prompt, user_prompt):
        self.calls.append(
            {"system_prompt": system_prompt, "user_prompt": user_prompt}
        )
        if self.error is not None:
            raise self.error
        return ChatCompletion(
            content=self.content,
            provider="stub-provider",
            model="stub-model",
            usage={
                "input_tokens": 120,
                "output_tokens": 240,
                "total_tokens": 360,
            },
            finish_reason="stop",
            latency_ms=42,
            request_id="stub-request-1",
            thinking_enabled=False,
        )


@pytest.fixture
def import_db(monkeypatch):
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
        NodeReviewState.__table__,
        NodeReviewCommand.__table__,
        NodeApproval.__table__,
        ServiceRequest.__table__,
        AuditLog.__table__,
        Report.__table__,
    ]
    for table in tables:
        for column in table.columns:
            if isinstance(column.type, (JSONB, ARRAY)):
                monkeypatch.setattr(column, "type", JSON())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine, expire_on_commit=False) as session:
        yield SessionAdapter(session)
    engine.dispose()


def consultant(actor_id=7, *, consultant_type="psychology"):
    return SimpleNamespace(
        id=actor_id,
        role="consultant",
        consultant_type=consultant_type,
        consultant_specialties=[],
        is_active=True,
    )


async def seed_workflow_case(
    db,
    *,
    validator_skill,
    actor_id=7,
    review_policy_version="six-node-review-v1",
    case_status="ACTIVE",
    instance_status="RUNNING",
    request_status="accepted",
    step_statuses=None,
    assigned_mingli=None,
    assigned_psychology=None,
):
    """Build a six-step RUNNING case with pinned validator skill bindings."""
    now = datetime.utcnow()
    bindings = {
        "report.final_validator": {
            "id": validator_skill.id,
            "version": validator_skill.version,
            "digest": specification_digest(validator_skill.specification_json),
        }
    }
    latest_version = await db.scalar(
        select(WorkflowVersion.version)
        .where(WorkflowVersion.workflow_key == "report.production")
        .order_by(WorkflowVersion.version.desc())
        .limit(1)
    )
    workflow_version = WorkflowVersion(
        workflow_key="report.production",
        name="Consultant workflow",
        version=(latest_version or 0) + 1,
        status="PUBLISHED",
        definition_json={"steps": []},
        created_at=now,
        published_at=now,
    )
    db.add(workflow_version)
    await db.flush()
    request = ServiceRequest(
        user_id=41,
        service_type="report",
        status=request_status,
        request_payload={"profile": {"name": "林女士"}},
        assigned_mingli_consultant_id=assigned_mingli,
        assigned_psychology_consultant_id=assigned_psychology,
        created_at=now,
        updated_at=now,
    )
    db.add(request)
    await db.flush()
    case = ReportCase(
        user_id=41,
        service_request_id=request.id,
        status=case_status,
        review_policy_version=review_policy_version,
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
            "skill_bindings": bindings,
        },
        application_submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(case)
    await db.flush()
    instance = WorkflowInstance(
        report_case_id=case.id,
        workflow_version_id=workflow_version.id,
        status=instance_status,
        created_at=now,
        updated_at=now,
        started_at=now,
    )
    db.add(instance)
    await db.flush()
    case.workflow_instance_id = instance.id
    overrides = step_statuses or {}
    steps = {}
    for index, step_key in enumerate(
        ("S1", "S2", "S3", "S4", "S5", "S6"), start=1
    ):
        status = overrides.get(step_key, "READY" if step_key == "S1" else "PENDING")
        task = StepTask(
            workflow_instance_id=instance.id,
            step_key=step_key,
            sequence_no=index,
            executor="HUMAN",
            status=status,
            required_capability=STEP_SPECIALTIES[step_key],
            activation_no=1 if status != "PENDING" else 0,
            config_snapshot={},
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        steps[step_key] = task
    await db.flush()
    return SimpleNamespace(
        case=case, request=request, instance=instance, steps=steps
    )


async def import_sample(
    db, seeded, *, actor, idempotency_key="import-key-1", gateway=None
):
    return await import_report_case(
        db,
        report_case=seeded.case,
        actor=actor,
        content=REPORT_TEXT,
        content_sha256=content_sha256(REPORT_TEXT),
        idempotency_key=idempotency_key,
        title="人生说明书",
        source_filename="report.md",
        normalization_gateway=gateway,
    )


async def import_text(
    db,
    seeded,
    *,
    text,
    actor,
    idempotency_key="import-key-1",
    gateway=None,
):
    return await import_report_case(
        db,
        report_case=seeded.case,
        actor=actor,
        content=text,
        content_sha256=content_sha256(text),
        idempotency_key=idempotency_key,
        title="人生说明书",
        source_filename="report.txt",
        normalization_gateway=gateway,
    )


# --- parser -----------------------------------------------------------------


def test_parse_report_content_accepts_markdown_bold_and_key_forms():
    sections = parse_report_content(
        "**你是谁**\n自我介绍\n\n### report.challenge\n卡点描述\n\n往哪去：\n行动方向\n"
    )

    assert [section.section_key for section in sections] == [
        "identity",
        "challenge",
        "direction",
    ]
    assert [section.fragment_key for section in sections] == [
        "report.identity",
        "report.challenge",
        "report.direction",
    ]
    assert sections[0].content == "自我介绍"
    assert sections[1].content == "卡点描述"
    assert sections[2].content == "行动方向"


def test_parse_report_content_reports_missing_sections():
    with pytest.raises(ReportImportError, match="report_import_sections_missing"):
        parse_report_content("# 你是谁\n只有一段\n\n# 卡在哪\n只差一段\n")


def test_parse_report_content_rejects_duplicate_sections():
    with pytest.raises(ReportImportError, match="report_import_duplicate_section"):
        parse_report_content(
            "# 你是谁\n甲\n\n# report.identity\n乙\n\n# 卡在哪\n丙\n\n# 往哪去\n丁\n"
        )


def test_parse_report_content_rejects_empty_section():
    with pytest.raises(ReportImportError, match="report_import_section_empty"):
        parse_report_content("# 你是谁\n\n# 卡在哪\n丙\n\n# 往哪去\n丁\n")


def test_parse_report_content_rejects_unstructured_and_oversized_content():
    with pytest.raises(ReportImportError, match="report_import_content_required"):
        parse_report_content("   \n")
    with pytest.raises(ReportImportError, match="report_import_format_invalid"):
        parse_report_content("这是一份没有章节标题的报告。")
    with pytest.raises(ReportImportError, match="report_import_content_too_long"):
        parse_report_content("x" * 100_001)
    with pytest.raises(ReportImportError, match="report_import_section_too_long"):
        parse_report_content(
            "# 你是谁\n{}\n\n# 卡在哪\n丙\n\n# 往哪去\n丁\n".format("x" * 30_001)
        )


def test_verify_content_hash_rejects_invalid_and_mismatched_digests():
    with pytest.raises(
        ReportImportError, match="report_import_content_sha256_invalid"
    ):
        normalize_declared_hash("not-a-hash")
    with pytest.raises(
        ReportImportError, match="report_import_content_sha256_mismatch"
    ):
        verify_content_hash("正文", "0" * 64)

    digest = content_sha256("正文")
    assert normalize_declared_hash(digest.upper()) == digest
    assert verify_content_hash("正文", digest) == digest


# --- import orchestration ---------------------------------------------------


@pytest.mark.asyncio
async def test_import_completes_authoring_steps_and_activates_final_review(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()

    actor = consultant()
    returned = await import_sample(import_db, seeded, actor=actor)
    await import_db.commit()

    assert returned.id == seeded.case.id
    assert seeded.case.review_policy_version == IMPORT_REVIEW_POLICY_VERSION
    assert seeded.case.status == "ACTIVE"
    for step_key in ("S1", "S2", "S3", "S4", "S5"):
        task = seeded.steps[step_key]
        assert task.status == "COMPLETED"
        assert (task.result_json or {})["imported"] is True
        assert task.completed_at is not None
    final_step = seeded.steps["S6"]
    assert final_step.status == "IN_REVIEW"
    assert final_step.assignee_id == actor.id
    assert seeded.request.status == "reviewing"
    assert seeded.request.assigned_psychology_consultant_id == actor.id
    assert seeded.request.assigned_consultant_id == actor.id

    import_run = await import_db.scalar(
        select(SkillRun).where(SkillRun.target_type == "REPORT_IMPORT")
    )
    assert import_run.status == "COMPLETED"
    assert import_run.target_key == content_sha256(REPORT_TEXT)
    assert import_run.context_snapshot["report_import_key"] == "import-key-1"

    plan = await import_db.scalar(
        select(NarrativePlan).where(NarrativePlan.report_case_id == seeded.case.id)
    )
    assert plan.status == "CONFIRMED"
    assert plan.is_current is True
    assert plan.selected_candidate_key == "imported-report-v1"
    assert plan.plan_json["content_plan"]["status"] == "READY"
    assert plan.plan_json["core_theme"] == "人生说明书"
    assert [
        item["fragment_key"] for item in plan.plan_json["content_plan"]["fragments"]
    ] == ["report.identity", "report.challenge", "report.direction"]

    fragments = list(
        await import_db.scalars(
            select(ContentFragmentRevision)
            .where(ContentFragmentRevision.report_case_id == seeded.case.id)
            .order_by(ContentFragmentRevision.fragment_key)
        )
    )
    assert [row.fragment_key for row in fragments] == [
        "report.challenge",
        "report.direction",
        "report.identity",
    ]
    for row in fragments:
        assert row.status == "CONFIRMED"
        assert row.is_current is True
        assert row.owner_step_task_id == final_step.id
        assert row.source_skill_run_id == import_run.id
        assert row.source_narrative_plan_id == plan.id
        assert row.source_snapshot["source"] == "consultant_import"

    audit = await import_db.scalar(
        select(AuditLog).where(AuditLog.action == "report_case.import")
    )
    assert audit is not None
    assert audit.resource_id == str(seeded.case.id)


@pytest.mark.asyncio
async def test_import_replay_with_same_key_and_content_is_idempotent(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    actor = consultant()

    await import_sample(import_db, seeded, actor=actor)
    await import_db.commit()
    await import_sample(import_db, seeded, actor=actor)
    await import_db.commit()

    runs = list(
        await import_db.scalars(
            select(SkillRun).where(SkillRun.target_type == "REPORT_IMPORT")
        )
    )
    plans = list(
        await import_db.scalars(
            select(NarrativePlan).where(NarrativePlan.report_case_id == seeded.case.id)
        )
    )
    assert len(runs) == 1
    assert len(plans) == 1


@pytest.mark.asyncio
async def test_import_rejects_conflicting_replay(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    actor = consultant()

    await import_sample(import_db, seeded, actor=actor)
    await import_db.commit()

    with pytest.raises(
        ReportImportError, match="report_import_idempotency_conflict"
    ):
        await import_sample(
            import_db, seeded, actor=actor, idempotency_key="import-key-2"
        )
    await import_db.rollback()

    other_text = REPORT_TEXT.replace("小范围尝试", "小范围试点")
    with pytest.raises(
        ReportImportError, match="report_import_idempotency_conflict"
    ):
        await import_report_case(
            import_db,
            report_case=seeded.case,
            actor=actor,
            content=other_text,
            content_sha256=content_sha256(other_text),
            idempotency_key="import-key-1",
        )


@pytest.mark.asyncio
async def test_import_rejects_content_already_used_by_another_case(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    first = await seed_workflow_case(import_db, validator_skill=validator_skill)
    second = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    actor = consultant()

    await import_sample(import_db, first, actor=actor)
    await import_db.commit()

    with pytest.raises(ReportImportError, match="report_import_duplicate_content"):
        await import_sample(
            import_db, second, actor=actor, idempotency_key="import-key-second"
        )


# --- model normalization layer ---------------------------------------------


async def _import_run(db):
    return await db.scalar(
        select(SkillRun).where(SkillRun.target_type == "REPORT_IMPORT")
    )


@pytest.mark.asyncio
async def test_standard_report_skips_the_model_layer(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    gateway = StubNormalizationGateway(
        error=AssertionError("model layer must not run for a standard report")
    )

    await import_sample(import_db, seeded, actor=consultant(), gateway=gateway)
    await import_db.commit()

    assert gateway.calls == []
    run = await _import_run(import_db)
    assert run.output_raw is None
    assert run.model_trace == {"used_model": False, "source": "local_parse"}
    assert run.context_snapshot["used_model_normalization"] is False
    assert run.context_snapshot["report_import_normalized_sha256"] == content_sha256(
        render_import_markdown(parse_report_content(REPORT_TEXT))
    )
    assert [item["section_key"] for item in run.output_parsed["sections"]] == [
        "identity",
        "challenge",
        "direction",
    ]


@pytest.mark.asyncio
async def test_unstructured_report_is_normalized_by_the_model(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    gateway = StubNormalizationGateway(content=NORMALIZED_TEXT)

    await import_text(
        import_db,
        seeded,
        text=FREEFORM_REPORT_TEXT,
        actor=consultant(),
        gateway=gateway,
    )
    await import_db.commit()

    assert len(gateway.calls) == 1
    assert FREEFORM_REPORT_TEXT in gateway.calls[0]["user_prompt"]
    assert "# 你是谁" in gateway.calls[0]["system_prompt"]
    assert "不得总结" in gateway.calls[0]["system_prompt"]

    expected_sections = parse_report_content(NORMALIZED_TEXT)
    expected_content = render_import_markdown(expected_sections)
    expected_hash = content_sha256(expected_content)
    original_hash = content_sha256(FREEFORM_REPORT_TEXT)

    run = await _import_run(import_db)
    assert run.target_key == original_hash
    assert run.output_raw == expected_content
    assert run.context_snapshot["report_import_sha256"] == original_hash
    assert run.context_snapshot["report_import_normalized_sha256"] == expected_hash
    assert run.context_snapshot["used_model_normalization"] is True
    assert run.model_trace["used_model"] is True
    assert run.model_trace["provider"] == "stub-provider"
    assert run.model_trace["model"] == "stub-model"
    assert run.model_trace["input_tokens"] == 120
    assert run.model_trace["output_tokens"] == 240
    assert run.model_trace["latency_ms"] == 42
    assert run.model_trace["output_validation"] == "passed"
    assert run.model_trace["trigger_parse_error"] == "report_import_format_invalid"
    assert run.model_trace["prompt_sha256"] == (
        run.input_snapshot["normalization_prompt_sha256"]
    )
    assert run.input_snapshot["content_sha256"] == original_hash
    assert run.input_snapshot["normalized_content_sha256"] == expected_hash

    plan = await import_db.scalar(
        select(NarrativePlan).where(NarrativePlan.report_case_id == seeded.case.id)
    )
    assert plan.plan_json["source"]["kind"] == "consultant_import"
    assert plan.plan_json["source"]["content_sha256"] == original_hash
    assert plan.plan_json["source"]["normalized_content_sha256"] == expected_hash
    assert plan.plan_json["source"]["used_model_normalization"] is True

    fragments = {
        row.fragment_key: row
        for row in await import_db.scalars(
            select(ContentFragmentRevision).where(
                ContentFragmentRevision.report_case_id == seeded.case.id
            )
        )
    }
    for section in expected_sections:
        assert fragments[section.fragment_key].content == section.content
        assert fragments[section.fragment_key].source_snapshot["content_sha256"] == (
            original_hash
        )
        assert fragments[section.fragment_key].source_snapshot[
            "normalized_content_sha256"
        ] == expected_hash

    audit = await import_db.scalar(
        select(AuditLog).where(AuditLog.action == "report_case.import")
    )
    audit_details = (
        audit.details if isinstance(audit.details, dict) else json.loads(audit.details)
    )
    assert audit_details["used_model_normalization"] is True
    assert audit_details["normalized_content_sha256"] == expected_hash
    assert seeded.steps["S6"].status == "IN_REVIEW"


@pytest.mark.asyncio
async def test_model_output_that_is_still_unstructured_is_rejected(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    gateway = StubNormalizationGateway(
        content="整理后的报告：这里仍然没有三段标题。"
    )

    with pytest.raises(ReportImportError, match="report_import_normalization_failed"):
        await import_text(
            import_db,
            seeded,
            text=FREEFORM_REPORT_TEXT,
            actor=consultant(),
            gateway=gateway,
        )
    await import_db.rollback()

    assert len(gateway.calls) == 1
    assert await _import_run(import_db) is None
    assert seeded.steps["S1"].status == "READY"
    assert seeded.case.review_policy_version == "six-node-review-v1"


@pytest.mark.asyncio
async def test_normalization_provider_failure_returns_a_stable_error(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    gateway = StubNormalizationGateway(error=RuntimeError("provider unreachable"))

    with pytest.raises(ReportImportError, match="report_import_normalization_failed"):
        await import_text(
            import_db,
            seeded,
            text=FREEFORM_REPORT_TEXT,
            actor=consultant(),
            gateway=gateway,
        )
    await import_db.rollback()

    assert await _import_run(import_db) is None
    assert seeded.steps["S1"].status == "READY"


@pytest.mark.asyncio
async def test_replaying_an_import_does_not_call_the_model_twice(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    gateway = StubNormalizationGateway(content=NORMALIZED_TEXT)
    actor = consultant()

    await import_text(
        import_db,
        seeded,
        text=FREEFORM_REPORT_TEXT,
        actor=actor,
        idempotency_key="normalized-key",
        gateway=gateway,
    )
    await import_db.commit()
    await import_text(
        import_db,
        seeded,
        text=FREEFORM_REPORT_TEXT,
        actor=actor,
        idempotency_key="normalized-key",
        gateway=gateway,
    )
    await import_db.commit()

    assert len(gateway.calls) == 1
    runs = list(
        await import_db.scalars(
            select(SkillRun).where(SkillRun.target_type == "REPORT_IMPORT")
        )
    )
    assert len(runs) == 1


@pytest.mark.asyncio
async def test_invalid_or_oversized_input_never_reaches_the_model(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    gateway = StubNormalizationGateway(
        error=AssertionError("model layer must not run for rejected input")
    )
    actor = consultant()
    oversized_section = (
        "# 你是谁\n{}\n\n# 卡在哪\n丙\n\n# 往哪去\n丁\n".format("x" * 30_001)
    )

    for text, code in (
        ("   \n", "report_import_content_required"),
        ("x" * 100_001, "report_import_content_too_long"),
        (oversized_section, "report_import_section_too_long"),
    ):
        with pytest.raises(ReportImportError, match=code):
            await import_text(
                import_db, seeded, text=text, actor=actor, gateway=gateway
            )
        await import_db.rollback()

    with pytest.raises(
        ReportImportError, match="report_import_content_sha256_mismatch"
    ):
        await import_report_case(
            import_db,
            report_case=seeded.case,
            actor=actor,
            content=FREEFORM_REPORT_TEXT,
            content_sha256="0" * 64,
            idempotency_key="normalized-key",
            normalization_gateway=gateway,
        )
    await import_db.rollback()

    assert gateway.calls == []


@pytest.mark.asyncio
async def test_non_importable_case_is_rejected_before_the_model_call(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(
        import_db,
        validator_skill=validator_skill,
        step_statuses={"S1": "IN_REVIEW"},
    )
    await import_db.commit()
    gateway = StubNormalizationGateway(
        error=AssertionError("model layer must not run for a non-importable case")
    )

    with pytest.raises(ReportImportError, match="report_import_case_not_importable"):
        await import_text(
            import_db,
            seeded,
            text=FREEFORM_REPORT_TEXT,
            actor=consultant(),
            gateway=gateway,
        )
    await import_db.rollback()

    assert gateway.calls == []


@pytest.mark.asyncio
async def test_import_rejects_cases_that_left_the_authoring_start(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    started = await seed_workflow_case(
        import_db,
        validator_skill=validator_skill,
        step_statuses={"S1": "IN_REVIEW"},
    )
    delivered = await seed_workflow_case(
        import_db, validator_skill=validator_skill, case_status="DELIVERED"
    )
    legacy = await seed_workflow_case(
        import_db,
        validator_skill=validator_skill,
        review_policy_version="legacy-manual-v1",
    )
    await import_db.commit()
    actor = consultant()

    for seeded in (started, delivered, legacy):
        with pytest.raises(
            ReportImportError, match="report_import_case_not_importable"
        ):
            await import_sample(import_db, seeded, actor=actor)
        await import_db.rollback()

    assert started.steps["S1"].status == "IN_REVIEW"
    assert all(
        started.steps[key].status == "PENDING" for key in ("S2", "S3", "S4", "S5", "S6")
    )


@pytest.mark.asyncio
async def test_import_is_forbidden_for_a_consultant_without_the_final_capability(
    import_db,
):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()

    with pytest.raises(ReportImportError, match="report_case_forbidden"):
        await import_sample(import_db, seeded, actor=consultant(consultant_type="mingli"))

    assert seeded.steps["S6"].assignee_id is None
    assert seeded.case.review_policy_version == "six-node-review-v1"


@pytest.mark.asyncio
async def test_admin_import_keeps_existing_professional_ownership(import_db):
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(
        import_db,
        validator_skill=validator_skill,
        assigned_mingli=5,
        assigned_psychology=6,
    )
    await import_db.commit()

    await import_sample(
        import_db,
        seeded,
        actor=SimpleNamespace(id=1, role="admin", is_active=True),
    )
    await import_db.commit()

    assert seeded.request.assigned_mingli_consultant_id == 5
    assert seeded.request.assigned_psychology_consultant_id == 6
    assert seeded.request.assigned_consultant_id == 5
    assert seeded.steps["S6"].assignee_id is None
    assert seeded.steps["S6"].status == "IN_REVIEW"


# --- gate integrity ---------------------------------------------------------


@pytest.mark.asyncio
async def test_imported_case_can_confirm_and_deliver_without_any_check(import_db):
    """The fast path has no check gate: the consultant's confirmation authorizes delivery."""
    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    actor = consultant()
    await import_sample(import_db, seeded, actor=actor)
    await import_db.commit()

    state = await quality_state(import_db, seeded.case)
    assert state.advisory_only is True
    assert state.can_approve is False
    assert state.can_finalize is True
    assert state.latest_validator_run is None
    assert state.open_count == 0

    await approve_case_final_gate(import_db, report_case=seeded.case, actor=actor)
    assert seeded.steps["S6"].status == "COMPLETED"
    assert seeded.case.status == "READY_TO_DELIVER"
    assert seeded.instance.status == "COMPLETED"
    gate_result = seeded.steps["S6"].result_json
    assert gate_result["advisory_only"] is True
    assert gate_result["final_gate_override"] is True
    assert gate_result["quality_status"] == "NOT_RUN"
    assert gate_result["validator_run_id"] is None
    assert gate_result["check_status"] == "NOT_RUN"
    assert gate_result["attested_by"] == actor.id
    assert gate_result["unresolved_advisories"] == []
    assert await import_db.scalar(select(func.count(NodeApproval.id))) == 0

    version = await deliver_report_case(
        import_db, report_case=seeded.case, actor=actor
    )
    assert seeded.case.status == "DELIVERED"
    assert seeded.request.status == "delivered"
    assert version.semantic_snapshot["quality"]["advisory_only"] is True
    assert version.semantic_snapshot["quality"]["validator_run_id"] is None
    assert version.semantic_snapshot["final_gate"]["result_json"]["advisory_only"] is True
    assert version.structured_data["narrative_plan"]["source"]["kind"] == (
        "consultant_import"
    )
    assert [item["section_key"] for item in version.structured_data["structured_sections"]] == [
        "identity",
        "challenge",
        "direction",
    ]
    assert version.semantic_snapshot["semantics"] == {
        "findings": [],
        "analysis_fragments": [],
        "evidence": [],
    }
    report = await import_db.scalar(select(Report).where(Report.user_id == 41))
    assert report is not None
    assert report.content_payload["summary"] == "人生说明书"


@pytest.mark.asyncio
async def test_imported_advisories_never_block_confirmation(
    import_db, monkeypatch
):
    """Findings stay advice; the consultant's attestation is the only authorization."""
    from app.application import skill_runtime

    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    actor = consultant()
    blocked_text = REPORT_TEXT.replace(
        "把可控的选择变成可验证的事实",
        "你注定发财，先等结果出现",
    )
    await import_report_case(
        import_db,
        report_case=seeded.case,
        actor=actor,
        content=blocked_text,
        content_sha256=content_sha256(blocked_text),
        idempotency_key="import-advisory-key",
    )
    await import_db.commit()

    queued = await queue_case_quality_run(
        import_db,
        report_case=seeded.case,
        actor_id=actor.id,
        idempotency_key="import-advisory-qa",
    )
    # A programmatic BLOCK becomes advice on the fast path instead of a stop.
    assert queued["status"] == "PENDING"
    assert queued["validator_run"] is not None

    pending = await quality_state(import_db, seeded.case)
    assert pending.advisory_only is True
    assert pending.can_approve is False
    assert pending.can_finalize is True
    assert pending.quality_status == "PROGRAMMATIC_BLOCKED"
    assert {item["issue_type"] for item in pending.unresolved_advisories} >= {
        "BLOCKED_EXPRESSION"
    }

    gateway = StubGateway(
        json.dumps(
            {
                "issues": [],
                "scorecard": {
                    "dimensions": {
                        key: {
                            "score": maximum,
                            "reason": "导入报告逐段核对完成。",
                            "fragment_keys": ["report.identity"],
                        }
                        for key, maximum in RUBRIC.items()
                    }
                },
            }
        )
    )
    monkeypatch.setattr(skill_runtime, "DeepSeekGateway", lambda: gateway)
    completed = await skill_runtime.execute_skill_run_record(
        import_db, queued["validator_run"].id
    )
    assert completed.status == "COMPLETED"

    state = await quality_state(import_db, seeded.case)
    assert state.advisory_only is True
    assert state.can_approve is False
    assert state.can_finalize is True
    assert state.open_count >= 1

    note = "已与来访者核对高风险表达，按咨询师判断保留原文交付。"
    await approve_case_final_gate(
        import_db, report_case=seeded.case, actor=actor, note=note
    )
    gate_result = seeded.steps["S6"].result_json
    assert gate_result["final_gate_approved"] is True
    assert gate_result["advisory_only"] is True
    assert gate_result["final_gate_override"] is True
    assert gate_result["validator_run_id"] == completed.id
    assert gate_result["check_status"] == "COMPLETED"
    assert gate_result["note"] == note
    assert [item["issue_type"] for item in gate_result["unresolved_advisories"]] == [
        "BLOCKED_EXPRESSION"
    ]
    assert await import_db.scalar(select(func.count(NodeApproval.id))) == 0

    version = await deliver_report_case(
        import_db, report_case=seeded.case, actor=actor
    )
    assert seeded.case.status == "DELIVERED"
    assert version.semantic_snapshot["quality"]["advisory_only"] is True
    assert version.semantic_snapshot["quality"]["final_gate_override"]["note"] == note


@pytest.mark.asyncio
async def test_import_keeps_programmatic_findings_visible(import_db):
    """The fast path skips authoring; programmatic findings still surface as advice."""
    from app.domains.quality.programmatic import collect_programmatic_issues

    validator_skill = await ensure_default_validator_skill_version(import_db)
    seeded = await seed_workflow_case(import_db, validator_skill=validator_skill)
    await import_db.commit()
    await import_sample(import_db, seeded, actor=consultant())
    await import_db.commit()

    issues, _, _ = await collect_programmatic_issues(import_db, seeded.case)
    assert issues == []

    blocked_text = REPORT_TEXT.replace(
        "把可控的选择变成可验证的事实",
        "你注定发财，先等结果出现",
    )
    assert blocked_text != REPORT_TEXT
    second_validator = await ensure_default_validator_skill_version(import_db)
    second = await seed_workflow_case(import_db, validator_skill=second_validator)
    await import_db.commit()
    await import_report_case(
        import_db,
        report_case=second.case,
        actor=consultant(),
        content=blocked_text,
        content_sha256=content_sha256(blocked_text),
        idempotency_key="import-key-blocked",
    )
    await import_db.commit()

    issues, _, _ = await collect_programmatic_issues(import_db, second.case)
    assert any(issue["issue_type"] == "BLOCKED_EXPRESSION" for issue in issues)

    queued = await queue_case_quality_run(
        import_db,
        report_case=second.case,
        actor_id=consultant().id,
        idempotency_key="import-key-blocked-qa",
    )
    assert queued["status"] != "PROGRAMMATIC_BLOCKED"
    assert queued["validator_run"] is not None


@pytest.mark.parametrize(
    "code,expected_status",
    [
        ("report_import_duplicate_content", 409),
        ("report_import_idempotency_conflict", 409),
        ("report_import_case_not_importable", 409),
        ("report_import_content_sha256_mismatch", 409),
        ("report_import_content_required", 422),
        ("report_import_format_invalid", 422),
        ("report_import_sections_missing", 422),
        ("report_import_section_empty", 422),
        ("report_import_section_too_long", 422),
        ("report_import_content_too_long", 422),
        ("report_import_duplicate_section", 422),
        ("report_import_content_sha256_invalid", 422),
        ("report_import_normalization_failed", 422),
        ("report_case_forbidden", 403),
    ],
)
def test_import_error_codes_map_to_http_status(code, expected_status):
    with pytest.raises(HTTPException) as raised:
        _workflow_error(ValueError(code))
    assert raised.value.status_code == expected_status
