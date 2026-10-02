from datetime import datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.api.v1.report_task_routes import router as report_task_router
from app.db.base import Base
from app.domains.audit.models import AuditLog  # noqa: F401
from app.domains.auth.models import AuthSession, StaffInvite  # noqa: F401
from app.domains.calendar.models import (
    CalendarEntry,
    CalendarRequest,
    DecisionLog,
    UserCalendar,
)  # noqa: F401
from app.domains.reports.models import Report, ReportTask  # noqa: F401
from app.domains.service_requests.models import (
    ServiceRequest,
    ServiceRequestDraft,
    ServiceRequestRevision,
    ServiceRequestTask,
)  # noqa: F401
from app.domains.workflow.definitions import (
    default_workflow_definition,
    validate_workflow_definition,
)
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowOutbox,
    WorkflowVersion,
)
from app.domains.workflow.service import (
    CompletionGate,
    cancel_case,
    complete_step,
    create_report_case,
    create_workflow_draft,
    publish_workflow_version,
    reopen_step,
    return_to_step,
    start_step,
)
from app.models.user import User  # noqa: F401


def test_default_definition_is_a_valid_sequential_workflow():
    definition = default_workflow_definition()
    assert [step["sequence_no"] for step in definition["steps"]] == list(range(1, 7))
    assert all(step["executor"] == "HUMAN" for step in definition["steps"])


def test_legacy_direct_report_generation_route_is_deprecated():
    route = next(
        route
        for route in report_task_router.routes
        if "POST" in route.methods and route.endpoint.__name__ == "create_report"
    )
    assert route.deprecated is True


def test_workflow_definition_rejects_duplicate_keys_and_sequence_gaps():
    duplicate = default_workflow_definition()
    duplicate["steps"][1]["step_key"] = duplicate["steps"][0]["step_key"]
    with pytest.raises(ValueError, match="workflow_step_duplicate"):
        validate_workflow_definition(duplicate)

    gap = default_workflow_definition()
    gap["steps"][1]["sequence_no"] = 7
    with pytest.raises(ValueError, match="workflow_step_sequence_invalid"):
        validate_workflow_definition(gap)


def test_completion_gate_requires_review_and_completed_predecessors():
    earlier = StepTask(step_key="S1", sequence_no=1, status="READY")
    current = StepTask(
        step_key="S2",
        sequence_no=2,
        status="IN_REVIEW",
        config_snapshot={"completion_policy": "MANUAL"},
    )
    with pytest.raises(ValueError, match="workflow_step_order_invalid"):
        CompletionGate.validate(current, [earlier, current])
    earlier.status = "COMPLETED"
    CompletionGate.validate(current, [earlier, current])
    current.status = "READY"
    with pytest.raises(ValueError, match="step_not_in_review"):
        CompletionGate.validate(current, [earlier, current])


class SyncSessionAdapter:
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


@pytest.fixture
def workflow_db():
    tables = [
        ReportCase.__table__,
        WorkflowVersion.__table__,
        WorkflowInstance.__table__,
        StepTask.__table__,
        WorkflowOutbox.__table__,
    ]
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine, expire_on_commit=False) as session:
        yield SyncSessionAdapter(session)
    engine.dispose()


async def _create_case(db: AsyncSession, service_request_id: int | None = None):
    version = WorkflowVersion(
        workflow_key="report.production",
        name="Consultant workflow",
        version=1,
        status="PUBLISHED",
        definition_json=default_workflow_definition(),
        created_at=datetime.utcnow(),
        published_at=datetime.utcnow(),
    )
    db.add(version)
    await db.flush()
    report_case = await create_report_case(
        db,
        user_id=1,
        service_request_id=service_request_id,
        source_report_task_id=None,
        application_snapshot={"context": {"goal": "test"}},
        workflow_version=version,
    )
    await db.flush()
    return report_case


@pytest.mark.asyncio
async def test_report_case_creation_is_idempotent_for_its_source_request(workflow_db):
    first = await _create_case(workflow_db, service_request_id=42)
    second = await create_report_case(
        workflow_db,
        user_id=1,
        service_request_id=42,
        source_report_task_id=None,
        application_snapshot={"context": {"goal": "changed"}},
    )
    count = await workflow_db.scalar(select(func.count(ReportCase.id)))
    assert second.id == first.id
    assert count == 1


async def _complete_step(db: AsyncSession, case_id: int, step_key: str):
    await start_step(db, case_id, step_key)
    await complete_step(db, case_id, step_key, result_json={"reviewed": True})


@pytest.mark.asyncio
async def test_manual_workflow_advances_sequentially_and_reaches_delivery_gate(
    workflow_db,
):
    report_case = await _create_case(workflow_db)
    tasks = list(
        (
            await workflow_db.scalars(
                select(StepTask)
                .where(
                    StepTask.workflow_instance_id == report_case.workflow_instance_id
                )
                .order_by(StepTask.sequence_no)
            )
        ).all()
    )
    assert [task.status for task in tasks] == [
        "READY",
        "PENDING",
        "PENDING",
        "PENDING",
        "PENDING",
        "PENDING",
    ]

    with pytest.raises(ValueError, match="step_not_in_review"):
        await complete_step(workflow_db, report_case.id, "S1")

    for task in tasks:
        await _complete_step(workflow_db, report_case.id, task.step_key)

    await workflow_db.refresh(report_case)
    instance = await workflow_db.get(WorkflowInstance, report_case.workflow_instance_id)
    assert report_case.status == "READY_TO_DELIVER"
    assert instance.status == "COMPLETED"
    assert all(task.status == "COMPLETED" for task in tasks)


@pytest.mark.asyncio
async def test_return_and_reopen_increment_activation_and_reset_downstream_steps(
    workflow_db,
):
    report_case = await _create_case(workflow_db)
    await _complete_step(workflow_db, report_case.id, "S1")
    await _complete_step(workflow_db, report_case.id, "S2")
    await start_step(workflow_db, report_case.id, "S3")

    await return_to_step(workflow_db, report_case.id, "S3", "S1", "重新核对基础信息")
    tasks = list(
        (
            await workflow_db.scalars(
                select(StepTask)
                .where(
                    StepTask.workflow_instance_id == report_case.workflow_instance_id
                )
                .order_by(StepTask.sequence_no)
            )
        ).all()
    )
    assert tasks[0].status == "READY"
    assert tasks[0].activation_no == 2
    assert [task.status for task in tasks[1:]] == ["PENDING"] * 5

    await _complete_step(workflow_db, report_case.id, "S1")
    assert tasks[1].status == "READY"
    assert tasks[1].activation_no == 2
    await reopen_step(workflow_db, report_case.id, "S1")
    assert tasks[0].status == "READY"
    assert tasks[0].activation_no == 3
    assert tasks[1].status == "PENDING"


@pytest.mark.asyncio
async def test_cancel_case_stops_active_work_and_preserves_completed_step_history(
    workflow_db,
):
    report_case = await _create_case(workflow_db)
    await _complete_step(workflow_db, report_case.id, "S1")

    cancelled = await cancel_case(
        workflow_db, report_case.id, reason="user_withdrew_request"
    )
    instance = await workflow_db.get(WorkflowInstance, report_case.workflow_instance_id)
    tasks = list(
        (
            await workflow_db.scalars(
                select(StepTask)
                .where(StepTask.workflow_instance_id == instance.id)
                .order_by(StepTask.sequence_no)
            )
        ).all()
    )
    event = await workflow_db.scalar(
        select(WorkflowOutbox).where(
            WorkflowOutbox.event_type == "report_case.cancelled"
        )
    )

    assert cancelled.status == "CANCELLED"
    assert instance.status == "CANCELLED"
    assert tasks[0].status == "COMPLETED"
    assert all(task.status == "CANCELLED" for task in tasks[1:])
    assert event.payload_json["reason"] == "user_withdrew_request"


@pytest.mark.asyncio
async def test_published_workflow_version_cannot_be_published_or_edited_again(
    workflow_db,
):
    draft = await create_workflow_draft(
        workflow_db,
        "report.test",
        "Test workflow",
        default_workflow_definition(),
        created_by=None,
    )
    await publish_workflow_version(workflow_db, draft.id, published_by=None)
    with pytest.raises(ValueError, match="workflow_version_immutable"):
        await publish_workflow_version(workflow_db, draft.id, published_by=None)


@pytest.mark.asyncio
async def test_outbox_publish_and_consume_are_idempotent(workflow_db, monkeypatch):
    from app.tasks import workflow_tasks

    class SessionContext:
        def __init__(self, session):
            self.session = session

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        workflow_tasks, "AsyncSessionLocal", lambda: SessionContext(workflow_db)
    )
    delivered = []
    monkeypatch.setattr(
        workflow_tasks.celery_app,
        "send_task",
        lambda name, args, task_id: delivered.append((name, args, task_id)),
    )

    report_case = await _create_case(workflow_db)
    event = await workflow_db.scalar(
        select(WorkflowOutbox)
        .where(WorkflowOutbox.event_type == "workflow.step.ready")
        .order_by(WorkflowOutbox.id)
        .limit(1)
    )
    before_publish = await workflow_tasks._consume_outbox_event(event.id)
    assert before_publish["status"] == "ready"
    assert await workflow_tasks._dispatch_pending_events() == 2
    assert await workflow_tasks._dispatch_pending_events() == 0
    await workflow_db.refresh(event)
    assert event.status == "PUBLISHED"
    assert len(delivered) == 2
    assert delivered[0][2] == f"workflow-outbox-{event.id}"

    first_delivery = await workflow_tasks._consume_outbox_event(event.id)
    repeated_delivery = await workflow_tasks._consume_outbox_event(event.id)
    task = await workflow_db.scalar(
        select(StepTask).where(
            StepTask.workflow_instance_id == report_case.workflow_instance_id,
            StepTask.step_key == "S1",
        )
    )
    assert first_delivery == repeated_delivery
    assert first_delivery["status"] == "ready"
    assert task.status == "READY"
    assert task.activation_no == 1
