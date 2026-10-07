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


def test_admin_user_timeline_includes_report_workflow_milestones_and_safe_audit_actions():
    now = datetime(2026, 10, 6, 8, tzinfo=timezone.utc)
    report_case = SimpleNamespace(
        id=81,
        service_request_id=17,
        workflow_instance_id=91,
        created_at=now - timedelta(days=5),
    )
    workflow_step = SimpleNamespace(
        id=101,
        workflow_instance_id=91,
        step_key="S1",
        sequence_no=1,
        executor="HUMAN",
        status="NEEDS_REVISION",
        activated_at=now - timedelta(days=4),
        started_at=now - timedelta(days=3),
        completed_at=None,
        updated_at=now - timedelta(days=2),
    )
    workflow_audit = SimpleNamespace(
        id=121,
        action="workflow.step.return",
        resource_id="81",
        details='{"step_key":"S1","reason":"private review note"}',
        created_at=now - timedelta(days=1),
    )

    events = build_admin_user_timeline(
        user_created_at=None,
        service_requests=[],
        calendar_requests=[],
        reports=[],
        report_tasks=[],
        calendars=[],
        decision_logs=[],
        audit_entries=[],
        report_cases=[report_case],
        workflow_steps=[workflow_step],
        workflow_audit_entries=[(workflow_audit, "咨询师甲")],
    )

    labels = [event["label"] for event in events]
    assert labels == [
        "退回报告流程节点",
        "报告第 1 步待修订",
        "咨询师开始处理报告第 1 步",
        "报告第 1 步已开放",
        "报告协作流程已建立",
    ]
    assert "申请 #17" in events[0]["description"]
    assert "第 1 步（S1）" in events[0]["description"]
    assert "咨询师甲" in events[0]["description"]
    assert all("private review note" not in str(event) for event in events)


def test_admin_user_timeline_keeps_business_workflow_milestones_without_audit_rows():
    now = datetime(2026, 10, 6, 8, tzinfo=timezone.utc)
    report_case = SimpleNamespace(
        id=81,
        service_request_id=17,
        workflow_instance_id=91,
        created_at=now - timedelta(days=2),
    )
    workflow_step = SimpleNamespace(
        id=101,
        workflow_instance_id=91,
        step_key="S1",
        sequence_no=1,
        executor="AI",
        status="COMPLETED",
        activated_at=now - timedelta(days=1, hours=5),
        started_at=now - timedelta(days=1, hours=4),
        completed_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )

    events = build_admin_user_timeline(
        user_created_at=None,
        service_requests=[],
        calendar_requests=[],
        reports=[],
        report_tasks=[],
        calendars=[],
        decision_logs=[],
        audit_entries=[],
        report_cases=[report_case],
        workflow_steps=[workflow_step],
    )

    assert {event["label"] for event in events} >= {
        "报告协作流程已建立",
        "报告第 1 步已开放",
        "AI开始处理报告第 1 步",
        "报告第 1 步已完成",
    }


def test_admin_user_timeline_includes_profile_feedback_calendar_and_record_updates_safely():
    now = datetime(2026, 10, 6, 8, tzinfo=timezone.utc)
    calendar_requests = [
        SimpleNamespace(
            id=41,
            status="fulfilled",
            created_at=now - timedelta(days=3),
            reviewed_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1),
        ),
        SimpleNamespace(
            id=42,
            status="failed",
            created_at=now - timedelta(days=2),
            reviewed_at=now - timedelta(days=1),
            updated_at=now - timedelta(hours=4),
        ),
    ]
    decision = SimpleNamespace(
        id=51,
        kind="action",
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(hours=3),
        log_date=now.date(),
        content="private action text",
        note="private note",
    )
    feedback = SimpleNamespace(
        id=61,
        service_request_id=17,
        calendar_request_id=None,
        feedback_type="COMPLAINT",
        rating=2,
        status="IN_PROGRESS",
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(hours=2),
        comment="private feedback comment",
        resolution="private resolution",
    )
    profile_audit = SimpleNamespace(
        id=71,
        action="user.profile.update",
        resource_type="user",
        resource_id="7",
        details='{"changed_fields":["name"]}',
        created_at=now - timedelta(hours=5),
    )
    feedback_audit = SimpleNamespace(
        id=72,
        action="service_feedback.update",
        resource_type="service_feedback",
        resource_id="61",
        details='{"from_status":"NEW","to_status":"IN_PROGRESS"}',
        created_at=now - timedelta(hours=2),
    )
    calendar_delivery_audit = SimpleNamespace(
        id=73,
        action="calendar.ai.deliver",
        resource_type="calendar",
        resource_id="88",
        details='{"calendar_request_id":41}',
        created_at=now - timedelta(days=1),
    )

    events = build_admin_user_timeline(
        user_created_at=None,
        service_requests=[],
        calendar_requests=calendar_requests,
        reports=[],
        report_tasks=[],
        calendars=[],
        decision_logs=[decision],
        service_feedback=[feedback],
        audit_entries=[
            (profile_audit, None),
            (feedback_audit, "管理员乙"),
            (calendar_delivery_audit, None),
        ],
    )

    labels = [event["label"] for event in events]
    assert "用户更新个人资料" in labels
    assert "日历生成已交付" in labels
    assert "日历生成失败" in labels
    assert "行动记录已更新" in labels
    assert "用户提交服务反馈" in labels
    assert "管理员跟进服务反馈（跟进中）" in labels
    calendar_delivery_events = [event for event in events if event["key"] == "audit:73"]
    assert len(calendar_delivery_events) == 1
    assert calendar_delivery_events[0]["resource_type"] == "calendar_request"
    assert calendar_delivery_events[0]["resource_id"] == "41"
    feedback_events = [event for event in events if event["resource_type"] == "service_feedback"]
    assert all("投诉" in event["description"] and "报告申请 #17" in event["description"] for event in feedback_events)
    assert all("2/5" in event["description"] for event in feedback_events)
    assert all(
        private_text not in str(events)
        for private_text in ("private action text", "private note", "private feedback comment", "private resolution")
    )
