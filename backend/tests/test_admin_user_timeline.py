from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.api.v1.admin_user_timeline_support import build_admin_user_timeline


def test_admin_user_timeline_merges_business_events_without_record_content():
    now = datetime(2026, 10, 6, 8, tzinfo=timezone.utc)
    request = SimpleNamespace(
        id=17,
        service_type="report",
        consultation_type="psychology",
        status="delivered",
        created_at=now - timedelta(days=3),
        accepted_at=now - timedelta(days=2),
        ai_started_at=None,
        ai_completed_at=None,
        reviewing_at=None,
        needs_info_at=None,
        failed_at=None,
        delivered_at=now - timedelta(days=1),
        withdrawn_at=None,
        rejected_at=None,
        request_payload={"context": {"current_challenge": "sensitive request text"}},
    )
    decision = SimpleNamespace(
        id=29,
        kind="decision",
        status="done",
        created_at=now - timedelta(hours=2),
        log_date=now.date(),
        content="sensitive decision text",
    )
    audit = SimpleNamespace(
        id=35,
        action="service_request.assignment.update",
        resource_type="service_request",
        resource_id="17",
        created_at=now - timedelta(hours=1),
    )

    events = build_admin_user_timeline(
        user_created_at=now - timedelta(days=10),
        service_requests=[request],
        calendar_requests=[],
        reports=[],
        report_tasks=[],
        calendars=[],
        decision_logs=[decision],
        audit_entries=[(audit, "管理员")],
        limit=30,
    )

    assert [event["label"] for event in events[:4]] == [
        "管理员调整咨询师分配",
        "决策记录已保存",
        "服务已交付",
        "咨询师已接单",
    ]
    assert events[-1]["label"] == "用户注册"
    assert all("sensitive" not in event["description"] for event in events)
    assert all(
        events[index]["occurred_at"] >= events[index + 1]["occurred_at"]
        for index in range(len(events) - 1)
    )


def test_admin_user_timeline_applies_requested_limit():
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    audit = SimpleNamespace(
        id=1,
        action="user.profile.update.admin",
        resource_type="user",
        resource_id="1",
        created_at=now + timedelta(hours=1),
    )
    events = build_admin_user_timeline(
        user_created_at=now,
        service_requests=[],
        calendar_requests=[],
        reports=[],
        report_tasks=[],
        calendars=[],
        decision_logs=[],
        audit_entries=[(audit, None)],
        limit=1,
    )

    assert len(events) == 1
    assert events[0]["key"] == "audit:1"


def test_admin_user_timeline_includes_report_and_calendar_events_safely():
    now = datetime(2026, 10, 6, 8, tzinfo=timezone.utc)
    calendar_request = SimpleNamespace(
        id=8,
        created_at=now - timedelta(days=4),
        reviewed_at=now - timedelta(days=3),
        status="approved",
        goal="sensitive calendar goal",
    )
    report = SimpleNamespace(
        id=12,
        title="人生说明书",
        created_at=now - timedelta(days=5),
        reviewed_at=now - timedelta(days=4),
        status="completed",
        is_deleted=False,
        content_payload={"secret": "sensitive report content"},
    )
    deleted_report = SimpleNamespace(
        id=13,
        title="已删除报告",
        created_at=now - timedelta(days=2),
        reviewed_at=None,
        status="completed",
        is_deleted=True,
    )
    report_task = SimpleNamespace(
        task_id="task-12345678",
        status="failed",
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=1),
        error="sensitive provider response",
    )
    calendar = SimpleNamespace(
        id=21,
        version_number=3,
        created_at=now - timedelta(days=6),
        published_at=now - timedelta(hours=1),
        status="published",
    )

    events = build_admin_user_timeline(
        user_created_at=None,
        service_requests=[],
        calendar_requests=[calendar_request],
        reports=[report, deleted_report],
        report_tasks=[report_task],
        calendars=[calendar],
        decision_logs=[],
        audit_entries=[],
    )

    labels = {event["label"] for event in events}
    assert {
        "日历申请已提交",
        "日历申请已审核",
        "报告已生成",
        "报告已审校",
        "报告任务失败",
        "日历版本已创建",
        "日历版本已发布",
    }.issubset(labels)
    assert all("sensitive" not in str(event) for event in events)
    assert all("13" not in event["key"] for event in events)
