from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.service_feedback import (
    list_admin_service_feedback,
    submit_service_feedback,
    update_admin_service_feedback,
)
from app.domains.feedback.models import ServiceFeedback
from app.domains.feedback.schemas import AdminServiceFeedbackUpdate, ServiceFeedbackCreate


class FailedAuditSavepoint:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FeedbackSession:
    def __init__(self, scalar_results):
        self.scalar = AsyncMock(side_effect=scalar_results)
        self.pending = []
        self.dirty = set()
        self.deleted = set()
        self.saved_audit_failure = False
        self.flush_calls = 0

    @property
    def new(self):
        return set(self.pending)

    def add(self, value):
        self.pending.append(value)

    async def flush(self, objects=None):
        self.flush_calls += 1
        if objects:
            self.saved_audit_failure = True
            raise RuntimeError("simulated audit constraint failure")
        for value in self.pending:
            if isinstance(value, ServiceFeedback) and value.id is None:
                value.id = 31
        self.pending.clear()

    def begin_nested(self):
        return FailedAuditSavepoint()


def delivered_report_request(**overrides):
    fields = {
        "id": 42,
        "user_id": 7,
        "service_type": "report",
        "status": "delivered",
        "result_type": "report",
        "result_id": 81,
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


@pytest.mark.asyncio
async def test_user_feedback_is_optional_post_delivery_and_audit_failure_is_isolated():
    db = FeedbackSession([delivered_report_request(), None])
    feedback = await submit_service_feedback(
        db,
        user=SimpleNamespace(id=7),
        data=ServiceFeedbackCreate(
            service_request_id=42,
            feedback_type="SUGGESTION",
            rating=4,
            comment="希望增加报告后的行动建议。",
        ),
    )

    assert feedback.status == "NEW"
    assert feedback.id == 31
    assert feedback.service_request_id == 42
    assert db.saved_audit_failure is True
    assert db.flush_calls == 2


@pytest.mark.asyncio
async def test_feedback_rejects_unowned_undelivered_and_duplicate_targets():
    with pytest.raises(ValueError, match="feedback_target_not_found"):
        await submit_service_feedback(
            FeedbackSession([None]),
            user=SimpleNamespace(id=7),
            data=ServiceFeedbackCreate(
                service_request_id=42,
                feedback_type="COMPLAINT",
                comment="交付内容与申请目标不符。",
            ),
        )

    with pytest.raises(ValueError, match="feedback_target_not_delivered"):
        await submit_service_feedback(
            FeedbackSession([delivered_report_request(status="reviewing")]),
            user=SimpleNamespace(id=7),
            data=ServiceFeedbackCreate(
                service_request_id=42,
                feedback_type="COMPLAINT",
                comment="交付内容与申请目标不符。",
            ),
        )

    with pytest.raises(ValueError, match="feedback_already_submitted"):
        await submit_service_feedback(
            FeedbackSession([delivered_report_request(), 3]),
            user=SimpleNamespace(id=7),
            data=ServiceFeedbackCreate(
                service_request_id=42,
                feedback_type="PRAISE",
                comment="咨询师的解释清楚且有帮助。",
            ),
        )


@pytest.mark.asyncio
async def test_calendar_feedback_requires_a_completed_calendar():
    completed = SimpleNamespace(
        id=61,
        user_id=7,
        status="fulfilled",
        calendar_id=93,
    )
    db = FeedbackSession([completed, None])
    feedback = await submit_service_feedback(
        db,
        user=SimpleNamespace(id=7),
        data=ServiceFeedbackCreate(
            calendar_request_id=61,
            feedback_type="PRAISE",
            comment="日历建议清楚，方便安排每天的行动。",
        ),
    )
    assert feedback.calendar_request_id == 61
    assert feedback.service_request_id is None

    completed.calendar_id = None
    with pytest.raises(ValueError, match="feedback_target_not_delivered"):
        await submit_service_feedback(
            FeedbackSession([completed]),
            user=SimpleNamespace(id=7),
            data=ServiceFeedbackCreate(
                calendar_request_id=61,
                feedback_type="PRAISE",
                comment="日历建议清楚，方便安排每天的行动。",
            ),
        )


@pytest.mark.asyncio
async def test_admin_feedback_requires_resolution_and_an_active_admin_assignee():
    feedback = SimpleNamespace(
        id=31,
        user_id=7,
        status="NEW",
        assigned_to=None,
        resolution=None,
        resolved_by=None,
        resolved_at=None,
        updated_by=None,
    )
    actor = SimpleNamespace(id=9)
    with pytest.raises(ValueError, match="feedback_resolution_required"):
        await update_admin_service_feedback(
            FeedbackSession([feedback]),
            feedback_id=31,
            actor=actor,
            data=AdminServiceFeedbackUpdate(status="RESOLVED"),
        )

    with pytest.raises(ValueError, match="feedback_assignee_invalid"):
        await update_admin_service_feedback(
            FeedbackSession([feedback, None]),
            feedback_id=31,
            actor=actor,
            data=AdminServiceFeedbackUpdate(
                status="IN_PROGRESS",
                assigned_to=12,
            ),
        )


@pytest.mark.asyncio
async def test_admin_feedback_update_keeps_main_state_when_audit_insert_fails():
    feedback = SimpleNamespace(
        id=31,
        user_id=7,
        status="NEW",
        assigned_to=None,
        resolution=None,
        resolved_by=None,
        resolved_at=None,
        updated_by=None,
    )
    admin = SimpleNamespace(id=12)
    db = FeedbackSession([feedback, admin])

    updated = await update_admin_service_feedback(
        db,
        feedback_id=31,
        actor=SimpleNamespace(id=9),
        data=AdminServiceFeedbackUpdate(
            status="RESOLVED",
            assigned_to=12,
            resolution="已核对报告交付记录，并向用户说明处理结果。",
        ),
    )

    assert updated.status == "RESOLVED"
    assert updated.assigned_to == 12
    assert updated.resolved_by == 9
    assert updated.resolved_at is not None
    assert db.saved_audit_failure is True


@pytest.mark.asyncio
async def test_admin_feedback_list_maps_service_and_user_context():
    feedback = SimpleNamespace(
        id=31,
        service_request_id=42,
        calendar_request_id=None,
        feedback_type="COMPLAINT",
        rating=2,
        comment="交付内容与申请目标不符。",
        status="NEW",
        assigned_to=None,
        resolution=None,
        resolved_by=None,
        resolved_at=None,
        created_at=datetime(2026, 10, 1),
        updated_at=datetime(2026, 10, 1),
    )
    user = SimpleNamespace(id=7, name="测试用户", phone="13800000000")
    service_request = SimpleNamespace(id=42, result_id=81, status="delivered")

    class Result:
        def all(self):
            return [(feedback, user, service_request, None)]

    db = SimpleNamespace(
        scalar=AsyncMock(return_value=1),
        execute=AsyncMock(return_value=Result()),
    )
    items, total = await list_admin_service_feedback(
        db,
        status="NEW",
        service_type="report",
        page=1,
        size=20,
    )

    assert total == 1
    assert items[0].user_name == "测试用户"
    assert items[0].service_type == "report"
    assert items[0].service_result_id == 81
    assert items[0].status == "NEW"
