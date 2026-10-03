from datetime import date
from types import SimpleNamespace

import pytest

from app.api.v1.report_cases import _authorize_step_action
from app.api.v1.service_request_api_support import project_report_case_status
from app.application.report_cases import (
    create_user_service_request,
    ensure_legacy_report_request,
)
from app.domains.service_requests.payloads import payload_from_create
from app.domains.service_requests.schemas import (
    ServiceProfileSnapshot,
    ServiceRequestCreate,
)
from fastapi import HTTPException
from unittest.mock import AsyncMock


def _profile():
    return ServiceProfileSnapshot(
        name="林一",
        gender="female",
        birth_year=1992,
        birth_month=2,
        birth_day=29,
        calendar_type="solar",
        time_accuracy="unknown",
    )


def test_report_application_keeps_context_and_profile_version_snapshot():
    context = {
        "focus_topics": ["career"],
        "current_challenge": "考虑转行",
        "expected_outcomes": ["方向指引"],
        "decision_description": {"stage": "early"},
    }
    data = ServiceRequestCreate(
        service_type="report",
        profile=_profile(),
        profile_version=7,
        context=context,
        selected_topics=["career"],
        idempotency_key="stable-report-submit-7",
    )
    user = SimpleNamespace(name="林一", profile_version=7)

    payload, key = payload_from_create(data, user)

    assert payload["profile_version"] == 7
    assert payload["context"] == context
    assert payload["selected_topics"] == ["career"]
    assert key == "stable-report-submit-7"
    data.context["decision_description"]["stage"] = "changed"
    assert payload["context"]["decision_description"]["stage"] == "early"


def test_report_application_rejects_stale_profile_version():
    data = ServiceRequestCreate(
        service_type="report",
        profile=_profile(),
        profile_version=6,
        context={"current_challenge": "重新选择"},
    )

    with pytest.raises(ValueError, match="profile_version_conflict"):
        payload_from_create(data, SimpleNamespace(name="林一", profile_version=7))


def test_calendar_request_payload_does_not_gain_report_snapshot_fields():
    data = ServiceRequestCreate(
        service_type="calendar",
        profile=_profile(),
        profile_version=99,
        context={"should_not_be_saved": True},
        start_date=date(2026, 10, 3),
    )

    payload, _ = payload_from_create(data, SimpleNamespace(name="林一", profile_version=7))

    assert payload["end_date"] == "2026-11-01"
    assert "profile_version" not in payload
    assert "context" not in payload


@pytest.mark.parametrize(
    ("case_status", "step_status", "fallback", "expected"),
    [
        ("ACTIVE", None, "submitted", "submitted"),
        ("ACTIVE", "IN_REVIEW", "accepted", "reviewing"),
        ("ACTIVE", "READY", "accepted", "accepted"),
        ("READY_TO_DELIVER", None, "accepted", "workflow_complete"),
        ("DELIVERED", None, "accepted", "delivered"),
    ],
)
def test_user_request_status_projects_from_case_workflow(case_status, step_status, fallback, expected):
    assert project_report_case_status(case_status, step_status, fallback) == expected


@pytest.mark.asyncio
async def test_consultant_step_access_checks_assignment_capability_and_current_step():
    case = SimpleNamespace(id=10, workflow_instance_id=20, service_request_id=30)
    assigned_request = SimpleNamespace(
        assigned_consultant_id=4, status="accepted"
    )
    active_step = SimpleNamespace(
        id=50,
        step_key="S1",
        status="IN_REVIEW",
        required_capability="consultant",
        assignee_id=4,
    )
    db = SimpleNamespace(
        get=AsyncMock(return_value=case),
        scalar=AsyncMock(side_effect=[assigned_request, active_step, active_step]),
    )

    found_case, found_step = await _authorize_step_action(
        db,
        case_id=10,
        step_key="S1",
        actor=SimpleNamespace(id=4, role="consultant"),
        require_current_review=True,
    )

    assert found_case is case
    assert found_step is active_step
    assert db.scalar.await_count == 3


@pytest.mark.asyncio
async def test_consultant_cannot_open_unassigned_case_or_ungranted_capability():
    case = SimpleNamespace(id=10, workflow_instance_id=20, service_request_id=30)
    db = SimpleNamespace(
        get=AsyncMock(return_value=case),
        scalar=AsyncMock(return_value=SimpleNamespace(assigned_consultant_id=8, status="accepted")),
    )
    with pytest.raises(HTTPException) as unassigned:
        await _authorize_step_action(
            db, 10, "S1", SimpleNamespace(id=4, role="consultant")
        )
    assert unassigned.value.status_code == 403

    db.scalar = AsyncMock(side_effect=[
        SimpleNamespace(assigned_consultant_id=4, status="accepted"),
        SimpleNamespace(
            id=50,
            step_key="S1",
            status="READY",
            required_capability="skill_editor",
            assignee_id=None,
        ),
    ])
    with pytest.raises(HTTPException) as missing_capability:
        await _authorize_step_action(
            db, 10, "S1", SimpleNamespace(id=4, role="consultant")
        )
    assert missing_capability.value.status_code == 403


@pytest.mark.asyncio
async def test_case_backed_report_cannot_use_legacy_service_request_workflow():
    request = SimpleNamespace(id=30, service_type="report")
    db = SimpleNamespace(scalar=AsyncMock(return_value=SimpleNamespace(id=81)))

    with pytest.raises(ValueError, match="report_case_workflow_required"):
        await ensure_legacy_report_request(db, request)

    db.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_calendar_request_keeps_legacy_service_request_workflow():
    db = SimpleNamespace(scalar=AsyncMock())

    await ensure_legacy_report_request(
        db, SimpleNamespace(id=30, service_type="calendar")
    )

    db.scalar.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_calendar_service_requests_must_start_from_a_delivered_report():
    with pytest.raises(ValueError, match="calendar_requires_delivered_report"):
        await create_user_service_request(
            SimpleNamespace(),
            SimpleNamespace(id=8),
            SimpleNamespace(service_type="calendar"),
        )
