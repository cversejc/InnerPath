"""Coverage for the isolated ``report.simple`` full-text report workflow."""

from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import ARRAY, JSON, create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.api.v1.report_cases import _workflow_error
from app.application import report_cases as report_cases_application
from app.application.simple_report_delivery import complete_simple_report_step
from app.db.base import Base
from app.domains.audit.models import AuditLog
from app.domains.content.models import CaseEvidenceItem, NarrativePlan
from app.domains.delivery.models import ReportVersion
from app.domains.delivery.simple_models import (
    SimpleReportVersion,
    SimpleReviewDecision,
    SimpleStepExecution,
    SimpleStepRevision,
)
from app.domains.delivery.simple_schemas import SimpleStepCompleteInput
from app.domains.quality.models import QAIssue
from app.domains.reports.models import Report
from app.domains.reports.schemas import ReportContext
from app.domains.service_requests.models import ServiceRequest
from app.domains.service_requests.payloads import payload_from_create
from app.domains.service_requests.schemas import (
    ServiceProfileSnapshot,
    ServiceRequestAssignmentUpdate,
    ServiceRequestCreate,
    ServiceRequestUpdate,
)
from app.domains.service_requests.staff import accept_service_request
from app.domains.skills.models import AISkillVersion, SkillExample, SkillRun
from app.domains.workflow.definitions import (
    DEFAULT_WORKFLOW_KEY,
    SIMPLE_WORKFLOW_KEY,
    case_workflow_key,
    default_workflow_definition,
    normalize_workflow_key,
    report_step_catalog,
)
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowOutbox,
    WorkflowVersion,
)
from app.domains.workflow.service import create_report_case, start_step
from app.domains.workflow.simple_definitions import (
    SIMPLE_PROTOCOL_AI_ASSISTED,
    SIMPLE_PROTOCOL_LEGACY,
    SIMPLE_STEP_KEYS,
    ai_assisted_simple_workflow_definition,
    case_simple_protocol,
    simple_workflow_definition,
)
from app.models.user import User


class SessionAdapter:
    """Minimal async facade over a synchronous SQLAlchemy session."""

    def __init__(self, session: Session):
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

    def begin_nested(self):
        return _AsyncContext(self.session.begin_nested())

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def get(self, model, identity):
        return self.session.get(model, identity)

    async def flush(self, objects=None):
        self.session.flush(objects=objects)

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    async def refresh(self, value):
        self.session.refresh(value)


class _AsyncContext:
    def __init__(self, transaction):
        self.transaction = transaction

    async def __aenter__(self):
        self.transaction.__enter__()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return self.transaction.__exit__(exc_type, exc, traceback)


@pytest.fixture
def simple_db(monkeypatch):
    tables = [
        User.__table__,
        ServiceRequest.__table__,
        Report.__table__,
        AuditLog.__table__,
        ReportCase.__table__,
        WorkflowVersion.__table__,
        WorkflowInstance.__table__,
        StepTask.__table__,
        WorkflowOutbox.__table__,
        SimpleReportVersion.__table__,
        SimpleStepExecution.__table__,
        SimpleStepRevision.__table__,
        SimpleReviewDecision.__table__,
        ReportVersion.__table__,
        QAIssue.__table__,
        NarrativePlan.__table__,
        CaseEvidenceItem.__table__,
        AISkillVersion.__table__,
        SkillExample.__table__,
        SkillRun.__table__,
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


def _profile_snapshot():
    return {
        "profile": {
            "name": "林一",
            "gender": "female",
            "birth_year": 1992,
            "birth_month": 3,
            "birth_day": 9,
            "calendar_type": "solar",
        },
        "context": {"current_challenge": "考虑转行"},
    }


async def _published_simple_version(db):
    version = WorkflowVersion(
        workflow_key=SIMPLE_WORKFLOW_KEY,
        name="简化报告流程",
        version=1,
        status="PUBLISHED",
        definition_json=simple_workflow_definition(),
        created_at=datetime.utcnow(),
        published_at=datetime.utcnow(),
    )
    db.add(version)
    await db.flush()
    return version


async def _simple_case(db, *, with_request: bool = True):
    request = None
    if with_request:
        request = ServiceRequest(
            user_id=1,
            service_type="report",
            status="submitted",
            request_payload={**_profile_snapshot(), "workflow_key": SIMPLE_WORKFLOW_KEY},
        )
        db.add(request)
        await db.flush()
    version = await _published_simple_version(db)
    report_case = await create_report_case(
        db,
        user_id=1,
        service_request_id=request.id if request is not None else None,
        source_report_task_id=None,
        application_snapshot=_profile_snapshot(),
        workflow_version=version,
    )
    await db.flush()
    return report_case, request


async def _consultant_actor(db, case_id: int, consultant_id: int = 7):
    tasks = list(
        (
            await db.scalars(
                select(StepTask)
                .where(StepTask.workflow_instance_id == case_id)
                .order_by(StepTask.sequence_no)
            )
        ).all()
    )
    for task in tasks:
        task.assignee_id = consultant_id
    await db.flush()
    return SimpleNamespace(id=consultant_id, role="consultant", is_active=True)


def test_simple_definition_follows_the_report_node_catalog():
    definition = simple_workflow_definition()
    production = default_workflow_definition()
    node_count = len(SIMPLE_STEP_KEYS)

    assert SIMPLE_STEP_KEYS == tuple(
        step["step_key"] for step in report_step_catalog()
    )
    assert SIMPLE_STEP_KEYS == ("S1", "S2", "S3", "S4", "S5", "S6")
    assert [step["step_key"] for step in definition["steps"]] == list(SIMPLE_STEP_KEYS)
    assert [step["name"] for step in definition["steps"]] == [
        step["name"] for step in production["steps"]
    ]
    assert [step["sequence_no"] for step in definition["steps"]] == list(
        range(1, node_count + 1)
    )
    assert {step["required_capability"] for step in definition["steps"]} == {"consultant"}
    assert [
        step["config"]["output_version"] for step in definition["steps"]
    ] == list(range(1, node_count + 1))
    assert [
        step["config"]["input_contract"] for step in definition["steps"]
    ] == ["user_info+report_text"] * node_count
    assert [
        bool(step["config"].get("final_gate")) for step in definition["steps"]
    ] == [False] * (node_count - 1) + [True]
    assert "collaboration_contract" not in definition


def test_ai_assisted_definition_keeps_the_same_business_nodes():
    definition = ai_assisted_simple_workflow_definition()

    assert definition["simple_protocol"] == SIMPLE_PROTOCOL_AI_ASSISTED
    assert definition["protocol_version"] == 1
    assert [step["step_key"] for step in definition["steps"]] == list(SIMPLE_STEP_KEYS)
    assert {step["executor"] for step in definition["steps"]} == {"HYBRID"}
    assert {
        step["config"]["execution_protocol"] for step in definition["steps"]
    } == {SIMPLE_PROTOCOL_AI_ASSISTED}
    assert all(
        step["config"]["requires_human_approval"] is True
        for step in definition["steps"]
    )
    assert all(
        step["config"]["allow_manual_edit"] is True
        for step in definition["steps"]
    )
    assert all(
        step["config"]["auto_retry_limit"] == 2 for step in definition["steps"]
    )
    assert [
        bool(step["config"].get("final_gate")) for step in definition["steps"]
    ] == [False] * (len(SIMPLE_STEP_KEYS) - 1) + [True]
    assert definition["steps"][-1]["config"]["generation_profile"] == "final_quality_gate"


def test_protocol_resolution_defaults_unknown_definitions_to_legacy():
    assert case_simple_protocol(SimpleNamespace(application_snapshot={})) == (
        SIMPLE_PROTOCOL_LEGACY
    )
    assert (
        case_simple_protocol(
            SimpleNamespace(
                application_snapshot={"simple_protocol": SIMPLE_PROTOCOL_AI_ASSISTED}
            )
        )
        == SIMPLE_PROTOCOL_AI_ASSISTED
    )
    assert (
        case_simple_protocol({"simple_protocol": SIMPLE_PROTOCOL_AI_ASSISTED})
        == SIMPLE_PROTOCOL_AI_ASSISTED
    )
    with pytest.raises(ValueError, match="simple_protocol_unsupported"):
        case_simple_protocol(
            SimpleNamespace(application_snapshot={"simple_protocol": "experimental"})
        )


@pytest.mark.asyncio
async def test_simple_versions_are_published_per_protocol(simple_db):
    legacy = await report_cases_application.ensure_simple_workflow_version(simple_db)
    same_legacy = await report_cases_application.ensure_simple_workflow_version(simple_db)
    ai_assisted = await report_cases_application.ensure_simple_workflow_version(
        simple_db, SIMPLE_PROTOCOL_AI_ASSISTED
    )
    same_ai_assisted = await report_cases_application.ensure_simple_workflow_version(
        simple_db, SIMPLE_PROTOCOL_AI_ASSISTED
    )

    assert same_legacy.id == legacy.id
    assert same_ai_assisted.id == ai_assisted.id
    assert legacy.id != ai_assisted.id
    assert ai_assisted.version == legacy.version + 1
    assert legacy.definition_json == simple_workflow_definition()
    assert ai_assisted.definition_json == ai_assisted_simple_workflow_definition()
    assert "simple_protocol" not in legacy.definition_json


@pytest.mark.asyncio
async def test_ai_case_freezes_its_execution_protocol(simple_db):
    version = await report_cases_application.ensure_simple_workflow_version(
        simple_db, SIMPLE_PROTOCOL_AI_ASSISTED
    )
    report_case = await create_report_case(
        simple_db,
        user_id=1,
        service_request_id=None,
        source_report_task_id=None,
        application_snapshot={"context": {}},
        workflow_version=version,
    )

    assert (
        report_case.application_snapshot["simple_protocol"]
        == SIMPLE_PROTOCOL_AI_ASSISTED
    )
    assert case_simple_protocol(report_case) == SIMPLE_PROTOCOL_AI_ASSISTED
    assert set(report_case.application_snapshot["skill_bindings"]) == {
        "report.s1_foundation_analysis",
        "report.s2_psychology_mapping",
        "report.s3_integration",
        "report.s4_mechanism_block_action",
        "report.fragment_authoring",
        "report.final_validator",
    }
    assert all(
        isinstance(binding["id"], int)
        for binding in report_case.application_snapshot["skill_bindings"].values()
    )


@pytest.mark.asyncio
async def test_legacy_case_does_not_gain_an_ai_protocol_marker(simple_db):
    version = await report_cases_application.ensure_simple_workflow_version(simple_db)
    report_case = await create_report_case(
        simple_db,
        user_id=1,
        service_request_id=None,
        source_report_task_id=None,
        application_snapshot={"context": {}},
        workflow_version=version,
    )

    assert "simple_protocol" not in report_case.application_snapshot
    assert case_simple_protocol(report_case) == SIMPLE_PROTOCOL_LEGACY


@pytest.mark.asyncio
async def test_simple_nodes_produce_one_version_each_and_deliver_on_the_last_node(
    simple_db,
):
    report_case, request = await _simple_case(simple_db)
    actor = await _consultant_actor(simple_db, report_case.workflow_instance_id)
    final_round = len(SIMPLE_STEP_KEYS)
    final_text = f"第 {final_round} 轮完整报告"

    assert report_case.application_snapshot["workflow_key"] == SIMPLE_WORKFLOW_KEY
    assert "framework_contract" not in report_case.application_snapshot
    assert "reasoning_contract" not in report_case.application_snapshot
    assert "collaboration_contract" not in report_case.application_snapshot
    assert "skill_bindings" not in report_case.application_snapshot

    versions = []
    for round_no, step_key in enumerate(SIMPLE_STEP_KEYS, start=1):
        await start_step(simple_db, report_case.id, step_key)
        version, report = await complete_simple_report_step(
            simple_db,
            case_id=report_case.id,
            step_key=step_key,
            actor=actor,
            report_text=f"第 {round_no} 轮完整报告",
            review_note=f"{step_key} 审核意见",
            final_gate_confirmed=round_no == final_round,
        )
        versions.append(version)
        assert version.version_label == f"v{round_no}.0"
        assert version.round_no == round_no
        assert version.source_step_key == step_key
        assert version.is_final is (round_no == final_round)
        if round_no < final_round:
            assert report is None
        else:
            assert report is not None
            assert report.summary == final_text
            assert report.content_payload["structured_sections"] == [
                {
                    "section_key": "report_body",
                    "section_title": "报告正文",
                    "content": final_text,
                }
            ]
            assert report.input_snapshot["profile"]["name"] == "林一"

    await simple_db.refresh(report_case)
    await simple_db.refresh(request)
    assert report_case.status == "DELIVERED"
    assert report_case.delivered_at is not None
    assert request.status == "delivered"
    assert request.result_type == "report"
    assert request.result_id == report.id

    stored = list(
        (
            await simple_db.scalars(
                select(SimpleReportVersion).order_by(SimpleReportVersion.version_no)
            )
        ).all()
    )
    assert [row.report_text for row in stored] == [
        f"第 {round_no} 轮完整报告"
        for round_no in range(1, final_round + 1)
    ]
    for table in (
        ReportVersion,
        QAIssue,
        NarrativePlan,
        CaseEvidenceItem,
        SkillRun,
    ):
        count = await simple_db.scalar(select(func.count()).select_from(table))
        assert count == 0, f"{table.__tablename__} should stay untouched"


@pytest.mark.asyncio
async def test_simple_nodes_reject_skipped_rounds_and_foreign_cases(simple_db):
    report_case, _request = await _simple_case(simple_db)
    actor = await _consultant_actor(simple_db, report_case.workflow_instance_id)
    first_key, second_key = SIMPLE_STEP_KEYS[0], SIMPLE_STEP_KEYS[1]

    with pytest.raises(ValueError, match="step_not_in_review"):
        await complete_simple_report_step(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=actor,
            report_text="未开始的节点",
        )

    await start_step(simple_db, report_case.id, first_key)
    with pytest.raises(ValueError, match="step_not_in_review"):
        await complete_simple_report_step(
            simple_db,
            case_id=report_case.id,
            step_key=second_key,
            actor=actor,
            report_text="跳过第一轮",
        )
    assert await simple_db.scalar(select(func.count(SimpleReportVersion.id))) == 0

    production_case = ReportCase(
        user_id=2,
        status="ACTIVE",
        application_snapshot={"workflow_key": DEFAULT_WORKFLOW_KEY},
        application_submitted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    simple_db.add(production_case)
    await simple_db.flush()
    production_version = WorkflowVersion(
        workflow_key=DEFAULT_WORKFLOW_KEY,
        name="咨询师报告生产流程",
        version=1,
        status="PUBLISHED",
        definition_json={"steps": []},
        created_at=datetime.utcnow(),
        published_at=datetime.utcnow(),
    )
    simple_db.add(production_version)
    await simple_db.flush()
    instance = WorkflowInstance(
        report_case_id=production_case.id,
        workflow_version_id=production_version.id,
        status="RUNNING",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    simple_db.add(instance)
    await simple_db.flush()
    production_case.workflow_instance_id = instance.id
    task = StepTask(
        workflow_instance_id=instance.id,
        step_key=first_key,
        sequence_no=1,
        executor="HUMAN",
        status="IN_REVIEW",
        required_capability="consultant",
        activation_no=1,
        config_snapshot={"output_version": 1},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    simple_db.add(task)
    await simple_db.flush()

    with pytest.raises(ValueError, match="workflow_key_mismatch"):
        await complete_simple_report_step(
            simple_db,
            case_id=production_case.id,
            step_key=first_key,
            actor=SimpleNamespace(id=7, role="consultant", is_active=True),
            report_text="生产流程不应走简化入口",
        )


@pytest.mark.asyncio
async def test_final_round_requires_explicit_confirmation(simple_db):
    report_case, _request = await _simple_case(simple_db, with_request=False)
    actor = await _consultant_actor(simple_db, report_case.workflow_instance_id)
    final_key = SIMPLE_STEP_KEYS[-1]
    for step_key in SIMPLE_STEP_KEYS[:-1]:
        await start_step(simple_db, report_case.id, step_key)
        await complete_simple_report_step(
            simple_db,
            case_id=report_case.id,
            step_key=step_key,
            actor=actor,
            report_text=f"{step_key} 报告",
        )
    await start_step(simple_db, report_case.id, final_key)

    with pytest.raises(ValueError, match="final_gate_approval_required"):
        await complete_simple_report_step(
            simple_db,
            case_id=report_case.id,
            step_key=final_key,
            actor=actor,
            report_text="未确认的终版报告",
        )
    assert (
        await simple_db.scalar(select(func.count(SimpleReportVersion.id)))
        == len(SIMPLE_STEP_KEYS) - 1
    )
    assert await simple_db.scalar(select(func.count(Report.id))) == 0


@pytest.mark.asyncio
async def test_simple_report_text_is_required_and_versions_are_immutable(simple_db):
    report_case, _request = await _simple_case(simple_db)
    actor = await _consultant_actor(simple_db, report_case.workflow_instance_id)
    first_key = SIMPLE_STEP_KEYS[0]
    await start_step(simple_db, report_case.id, first_key)

    with pytest.raises(ValueError, match="simple_report_text_required"):
        await complete_simple_report_step(
            simple_db,
            case_id=report_case.id,
            step_key=first_key,
            actor=actor,
            report_text="   ",
        )

    version, _report = await complete_simple_report_step(
        simple_db,
        case_id=report_case.id,
        step_key=first_key,
        actor=actor,
        report_text="第一版报告",
    )
    version.report_text = "被篡改的报告"
    with pytest.raises(ValueError, match="simple_report_version_immutable"):
        await simple_db.flush()


def test_simple_completion_payload_rejects_forged_version_fields():
    with pytest.raises(ValidationError):
        SimpleStepCompleteInput(report_text="报告", version_no=2)
    with pytest.raises(ValidationError):
        SimpleStepCompleteInput(report_text="报告", is_final=True)
    with pytest.raises(ValidationError):
        SimpleStepCompleteInput(report_text="报告", final_gate_confirmed="yes")
    with pytest.raises(ValidationError):
        SimpleStepCompleteInput(report_text="")
    assert (
        SimpleStepCompleteInput(report_text="报告", final_gate_confirmed=True)
        .final_gate_confirmed
        is True
    )


def test_workflow_key_normalization_defaults_applications_and_keeps_legacy_production():
    assert normalize_workflow_key(None) == SIMPLE_WORKFLOW_KEY
    assert normalize_workflow_key("") == SIMPLE_WORKFLOW_KEY
    assert normalize_workflow_key(DEFAULT_WORKFLOW_KEY) == DEFAULT_WORKFLOW_KEY
    assert normalize_workflow_key("report.simple") == SIMPLE_WORKFLOW_KEY
    with pytest.raises(ValueError, match="workflow_key_unsupported"):
        normalize_workflow_key("report.experimental")
    assert (
        case_workflow_key(SimpleNamespace(application_snapshot={}))
        == DEFAULT_WORKFLOW_KEY
    )
    assert (
        case_workflow_key(SimpleNamespace(application_snapshot={"workflow_key": ""}))
        == DEFAULT_WORKFLOW_KEY
    )
    assert case_workflow_key({"workflow_key": SIMPLE_WORKFLOW_KEY}) == SIMPLE_WORKFLOW_KEY


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        ("workflow_key_mismatch", 409),
        ("workflow_key_locked", 409),
        ("simple_report_version_immutable", 409),
        ("simple_report_text_required", 422),
        ("step_not_current", 409),
        ("step_not_in_review", 409),
        ("final_gate_approval_required", 409),
        ("workflow_step_order_invalid", 409),
        ("step_task_not_found", 404),
    ],
)
def test_simple_workflow_errors_map_to_http_statuses(code, expected_status):
    with pytest.raises(HTTPException) as error:
        _workflow_error(ValueError(code))
    assert error.value.status_code == expected_status
    assert error.value.detail == code


def test_service_request_payload_defaults_to_simple_and_keeps_explicit_keys():
    data = ServiceRequestCreate(
        service_type="report",
        workflow_key=SIMPLE_WORKFLOW_KEY,
        profile=ServiceProfileSnapshot(
            name="林一",
            gender="female",
            birth_year=1992,
            birth_month=3,
            birth_day=9,
            calendar_type="solar",
            time_accuracy="unknown",
        ),
        context=ReportContext(
            focus_topics=["career"],
            current_challenge="考虑转行",
            expected_outcomes=["career"],
        ),
        idempotency_key="simple-report-1",
    )
    payload, _key = payload_from_create(
        data, SimpleNamespace(name="林一", profile_version=1)
    )
    assert payload["workflow_key"] == SIMPLE_WORKFLOW_KEY

    standard_payload, _key = payload_from_create(
        ServiceRequestCreate(
            service_type="report",
            workflow_key=DEFAULT_WORKFLOW_KEY,
            profile=ServiceProfileSnapshot(
                name="林一",
                gender="female",
                birth_year=1992,
                birth_month=3,
                birth_day=9,
                calendar_type="solar",
                time_accuracy="unknown",
            ),
            context=ReportContext(
                focus_topics=["career"],
                current_challenge="考虑转行",
                expected_outcomes=["career"],
            ),
            idempotency_key="standard-report-1",
        ),
        SimpleNamespace(name="林一", profile_version=1),
    )
    assert standard_payload["workflow_key"] == DEFAULT_WORKFLOW_KEY

    default_payload, _key = payload_from_create(
        ServiceRequestCreate(
            service_type="report",
            profile=ServiceProfileSnapshot(
                name="林一",
                gender="female",
                birth_year=1992,
                birth_month=3,
                birth_day=9,
                calendar_type="solar",
                time_accuracy="unknown",
            ),
            context=ReportContext(
                focus_topics=["career"],
                current_challenge="考虑转行",
                expected_outcomes=["career"],
            ),
            idempotency_key="default-report-1",
        ),
        SimpleNamespace(name="林一", profile_version=1),
    )
    assert default_payload["workflow_key"] == SIMPLE_WORKFLOW_KEY

    with pytest.raises(ValueError, match="workflow_key_unsupported"):
        payload_from_create(
            ServiceRequestCreate(
                service_type="report",
                workflow_key="report.experimental",
                profile=ServiceProfileSnapshot(
                    name="林一",
                    gender="female",
                    birth_year=1992,
                    birth_month=3,
                    birth_day=9,
                    calendar_type="solar",
                    time_accuracy="unknown",
                ),
                context=ReportContext(
                    focus_topics=["career"],
                    current_challenge="考虑转行",
                    expected_outcomes=["career"],
                ),
                idempotency_key="unknown-report-1",
            ),
            SimpleNamespace(name="林一", profile_version=1),
        )


def test_service_request_update_cannot_switch_workflow_after_creation():
    request = SimpleNamespace(
        service_type="report",
        status="submitted",
        profile_version=1,
        request_payload={
            "workflow_key": SIMPLE_WORKFLOW_KEY,
            "profile": {"name": "林一"},
            "context": {},
        },
    )
    user = SimpleNamespace(
        id=1, name="林一", profile_version=1, profile_snapshot=None
    )

    from app.domains.service_requests.payloads import payload_from_update

    with pytest.raises(ValueError, match="workflow_key_locked"):
        payload_from_update(
            request,
            ServiceRequestUpdate(workflow_key=DEFAULT_WORKFLOW_KEY),
            user,
        )


@pytest.mark.asyncio
async def test_simple_application_skips_production_workflow_and_evidence(monkeypatch):
    simple_version = SimpleNamespace(
        id=91, workflow_key=SIMPLE_WORKFLOW_KEY, version=1
    )
    created = {}
    request = SimpleNamespace(
        id=55,
        status="submitted",
        request_payload={"workflow_key": SIMPLE_WORKFLOW_KEY},
    )
    report_case = SimpleNamespace(
        id=77, application_snapshot={"workflow_key": SIMPLE_WORKFLOW_KEY}
    )

    async def create_request(db, user, data, *, audit_context=None, commit=True):
        return request

    async def create_case(db, **kwargs):
        created.update(kwargs)
        return report_case

    async def fail_production(db):
        raise AssertionError("production workflow must not be used")

    async def fail_evidence(**kwargs):
        raise AssertionError("simplified applications must not sync evidence")

    monkeypatch.setattr(
        report_cases_application, "create_service_request", create_request
    )
    monkeypatch.setattr(
        report_cases_application,
        "get_report_case_for_service_request",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        report_cases_application,
        "ensure_simple_workflow_version",
        AsyncMock(return_value=simple_version),
    )
    monkeypatch.setattr(
        report_cases_application,
        "ensure_collaborative_workflow_version",
        fail_production,
    )
    monkeypatch.setattr(
        report_cases_application, "create_report_case", create_case
    )
    monkeypatch.setattr(
        report_cases_application, "sync_application_evidence", fail_evidence
    )
    db = SimpleNamespace(
        commit=AsyncMock(), rollback=AsyncMock(), refresh=AsyncMock(), scalar=AsyncMock()
    )

    returned_request, returned_case = (
        await report_cases_application.create_user_service_request(
            db,
            SimpleNamespace(id=1),
            ServiceRequestCreate(
                service_type="report",
                workflow_key=SIMPLE_WORKFLOW_KEY,
                profile=ServiceProfileSnapshot(
                    name="林一",
                    gender="female",
                    birth_year=1992,
                    birth_month=3,
                    birth_day=9,
                    calendar_type="solar",
                    time_accuracy="unknown",
                ),
                idempotency_key="simple-report-2",
            ),
        )
    )

    assert returned_request is request
    assert returned_case is report_case
    assert created["workflow_version"] is simple_version


@pytest.mark.asyncio
async def test_any_active_consultant_can_accept_a_simple_case(simple_db):
    report_case, request = await _simple_case(simple_db)
    consultant = User(
        id=7,
        phone="test-7",
        name="普通咨询师",
        role="consultant",
        is_active=True,
        consultant_type=None,
        consultant_specialties=[],
    )
    simple_db.add(consultant)
    await simple_db.flush()

    accepted = await accept_service_request(simple_db, request.id, consultant)

    assert accepted.status == "accepted"
    assert accepted.assigned_consultant_id == consultant.id
    tasks = list(
        (
            await simple_db.scalars(
                select(StepTask)
                .where(StepTask.workflow_instance_id == report_case.workflow_instance_id)
                .order_by(StepTask.sequence_no)
            )
        ).all()
    )
    assert [task.assignee_id for task in tasks] == [consultant.id] * len(
        SIMPLE_STEP_KEYS
    )
    assert [task.status for task in tasks] == ["READY"] + ["PENDING"] * (
        len(SIMPLE_STEP_KEYS) - 1
    )


@pytest.mark.asyncio
async def test_admin_assignment_fans_out_a_simple_case_without_specialty_coverage(
    simple_db,
):
    from app.api.v1.service_request_admin_routes import update_request_assignment

    report_case, request = await _simple_case(simple_db)
    # Integrated delivery would normally demand both specialties; the
    # simplified workflow assigns all rounds to one consultant instead.
    request.consultation_type = "integrated"
    consultant = User(
        id=9,
        phone="test-9",
        name="普通咨询师",
        role="consultant",
        is_active=True,
        consultant_type=None,
        consultant_specialties=[],
    )
    admin = User(
        id=21,
        phone="test-admin",
        name="管理员",
        role="admin",
        is_active=True,
    )
    simple_db.add(consultant)
    simple_db.add(admin)
    await simple_db.flush()

    http_request = Request(
        {
            "type": "http",
            "method": "PATCH",
            "path": f"/api/v1/admin/service-requests/{request.id}/assignment",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
    )

    response = await update_request_assignment(
        request_id=request.id,
        data=ServiceRequestAssignmentUpdate(consultant_id=consultant.id),
        request=http_request,
        current_user=admin,
        db=simple_db,
    )

    assert response.assigned_consultant_id == consultant.id
    assert response.consultation_type == "integrated"
    assert response.status == "accepted"
    tasks = list(
        (
            await simple_db.scalars(
                select(StepTask)
                .where(StepTask.workflow_instance_id == report_case.workflow_instance_id)
                .order_by(StepTask.sequence_no)
            )
        ).all()
    )
    assert [task.step_key for task in tasks] == list(SIMPLE_STEP_KEYS)
    assert [task.assignee_id for task in tasks] == [consultant.id] * len(
        SIMPLE_STEP_KEYS
    )


def test_simple_routes_are_registered():
    from app.main import app

    routes = {
        (path, method.upper())
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.lower() in {"get", "post"}
    }
    assert {
        ("/api/v1/report-cases/{case_id}/simple/versions", "GET"),
        ("/api/v1/report-cases/{case_id}/simple/steps/{step_key}/complete", "POST"),
    }.issubset(routes)
