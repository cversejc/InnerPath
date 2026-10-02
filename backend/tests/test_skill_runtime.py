from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domains.skills.definitions import (
    DEFAULT_SKILL_KEY,
    default_skill_specification,
    validate_skill_specification,
)
from app.domains.skills.models import AISkillVersion, SkillRun
from app.domains.skills.runtime import ModelCompletion, execute_skill
from app.domains.skills.service import (
    create_skill_run,
    create_skill_draft,
    ensure_default_skill_version,
    publish_skill_version,
    update_skill_draft,
)
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
        WorkflowVersion.__table__,
        ReportCase.__table__,
        WorkflowInstance.__table__,
        StepTask.__table__,
        WorkflowOutbox.__table__,
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
    assert authoring["config"]["skill_version_id"] == 1


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
