from datetime import datetime

import pytest

from app.domains.service_requests.models import ServiceRequest
from app.domains.service_requests.staff import (
    accept_service_request,
    release_service_request,
    staff_can_access,
)
from app.domains.workflow.models import (
    ReportCase,
    StepTask,
    WorkflowInstance,
    WorkflowVersion,
)
from app.domains.workflow.service import assign_step
from app.models.user import User
from tests.test_calendar_production_chain import chain_db  # noqa: F401


async def seed_release_case(db, *, collaboration=True):
    user = User(phone="13800009901", name="退回测试用户")
    mingli = User(
        phone="13800009902",
        name="命理顾问",
        role="consultant",
        consultant_type="mingli",
        is_active=True,
    )
    psychology = User(
        phone="13800009903",
        name="心理顾问",
        role="consultant",
        consultant_type="psychology",
        is_active=True,
    )
    mingli_other = User(
        phone="13800009904",
        name="命理顾问二",
        role="consultant",
        consultant_type="mingli",
        is_active=True,
    )
    admin = User(phone="13800009905", name="运营管理员", role="admin")
    db.add_all([user, mingli, psychology, mingli_other, admin])
    await db.flush()

    snapshot = {}
    if collaboration:
        snapshot["collaboration_contract"] = {"version": 1}
    request = ServiceRequest(
        user_id=user.id,
        service_type="report",
        status="reviewing",
        request_payload={},
        consultation_type="integrated",
        assigned_consultant_id=mingli.id,
        assigned_mingli_consultant_id=mingli.id,
        assigned_psychology_consultant_id=psychology.id,
        accepted_at=datetime.utcnow(),
    )
    db.add(request)
    await db.flush()

    version = WorkflowVersion(
        workflow_key="report.production",
        name="Release test",
        version=1,
        status="PUBLISHED",
        definition_json={"steps": []},
        created_at=datetime.utcnow(),
    )
    db.add(version)
    await db.flush()
    case = ReportCase(
        user_id=user.id,
        service_request_id=request.id,
        status="ACTIVE",
        review_policy_version="six-node-review-v1",
        application_snapshot=snapshot,
        application_submitted_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(case)
    await db.flush()
    instance = WorkflowInstance(
        report_case_id=case.id,
        workflow_version_id=version.id,
        status="RUNNING",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        started_at=datetime.utcnow(),
    )
    db.add(instance)
    await db.flush()
    case.workflow_instance_id = instance.id

    specialties = {
        "S1": "mingli",
        "S2": "mingli",
        "S3": "mingli",
        "S4": "psychology",
        "S5": "psychology",
        "S6": "psychology",
    }
    tasks = {}
    for index, (step_key, specialty) in enumerate(specialties.items(), start=1):
        task = StepTask(
            workflow_instance_id=instance.id,
            step_key=step_key,
            sequence_no=index,
            executor="HYBRID",
            status="COMPLETED" if index <= 5 else "IN_REVIEW",
            required_capability=specialty,
            assignee_id=mingli.id if specialty == "mingli" else psychology.id,
            activation_no=1,
            config_snapshot={},
            result_json={"draft": f"{step_key}-result"} if index == 1 else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(task)
        tasks[step_key] = task
    await db.commit()
    return request, case, tasks, mingli, psychology, mingli_other, admin


@pytest.mark.asyncio
async def test_consultant_release_returns_request_to_pool_and_preserves_results(chain_db):
    request, _case, tasks, mingli, _psychology, _mingli_other, _admin = await seed_release_case(chain_db)

    released = await release_service_request(
        chain_db,
        request.id,
        mingli,
        "mingli",
        reason="改为全部由心理顾问跟进",
    )

    assert released.assigned_mingli_consultant_id is None
    assert released.assigned_psychology_consultant_id == _psychology.id
    assert released.assigned_consultant_id == _psychology.id
    assert released.status == "reviewing"
    for step_key in ("S1", "S2", "S3"):
        assert tasks[step_key].assignee_id is None
        assert tasks[step_key].status == "COMPLETED"
    assert tasks["S4"].assignee_id == _psychology.id
    assert staff_can_access(released, mingli) is False
    assert staff_can_access(released, _psychology) is True


@pytest.mark.asyncio
async def test_released_specialty_can_be_accepted_again_with_progress_kept(chain_db):
    request, _case, tasks, mingli, _psychology, _mingli_other, _admin = await seed_release_case(chain_db)
    await release_service_request(chain_db, request.id, mingli, "mingli")

    accepted = await accept_service_request(chain_db, request.id, mingli)

    assert accepted.assigned_mingli_consultant_id == mingli.id
    assert accepted.status == "reviewing"
    assert tasks["S1"].assignee_id == mingli.id
    assert tasks["S1"].status == "COMPLETED"


@pytest.mark.asyncio
async def test_released_specialty_can_be_taken_over_by_another_consultant(chain_db):
    request, _case, tasks, mingli, _psychology, mingli_other, _admin = await seed_release_case(chain_db)
    await release_service_request(chain_db, request.id, mingli, "mingli")

    accepted = await accept_service_request(chain_db, request.id, mingli_other)

    assert accepted.assigned_mingli_consultant_id == mingli_other.id
    assert accepted.assigned_psychology_consultant_id == _psychology.id
    assert accepted.status == "reviewing"
    assert tasks["S3"].assignee_id == mingli_other.id
    assert tasks["S3"].status == "COMPLETED"
    assert tasks["S4"].assignee_id == _psychology.id


@pytest.mark.asyncio
async def test_all_specialties_released_returns_request_to_submitted_pool(chain_db):
    request, _case, tasks, mingli, psychology, _mingli_other, _admin = await seed_release_case(chain_db)

    await release_service_request(chain_db, request.id, mingli, "mingli")
    released = await release_service_request(chain_db, request.id, psychology, "psychology")

    assert released.assigned_consultant_id is None
    assert released.assigned_mingli_consultant_id is None
    assert released.assigned_psychology_consultant_id is None
    assert released.status == "submitted"
    assert released.accepted_at is None
    assert all(task.assignee_id is None for task in tasks.values())


@pytest.mark.asyncio
async def test_completed_node_reassignment_requires_admin_force(chain_db):
    request, case, tasks, _mingli, _psychology, mingli_other, admin = await seed_release_case(chain_db)

    with pytest.raises(ValueError, match="step_assignment_locked"):
        await assign_step(chain_db, case.id, "S1", mingli_other.id)

    await assign_step(chain_db, case.id, "S1", mingli_other.id, force=True)

    assert tasks["S1"].assignee_id == mingli_other.id
    assert tasks["S1"].status == "COMPLETED"
    assert tasks["S1"].result_json == {"draft": "S1-result"}
    assert request.assigned_mingli_consultant_id == mingli_other.id
    assert admin.role == "admin"
