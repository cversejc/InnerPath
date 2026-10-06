from datetime import datetime, timezone

_SERVICE_REQUEST_STAGES = (
    ("created_at", "申请已提交"),
    ("accepted_at", "咨询师已接单"),
    ("ai_started_at", "开始生成初稿"),
    ("ai_completed_at", "初稿生成完成"),
    ("reviewing_at", "进入人工审校"),
    ("needs_info_at", "等待补充信息"),
    ("failed_at", "处理失败"),
    ("delivered_at", "服务已交付"),
    ("withdrawn_at", "用户撤回申请"),
    ("rejected_at", "申请已关闭"),
)

_CONSULTATION_LABELS = {
    "metaphysics": "命理",
    "mingli": "命理",
    "psychology": "心理",
    "integrated": "综合",
}

_AUDIT_ACTION_LABELS = {
    "user.profile.update.admin": "管理员更新用户资料",
    "user.status.update": "管理员调整账号状态",
    "user.role.update": "管理员调整账号角色",
    "user.password.reset": "管理员执行账号安全操作",
    "service_request.assignment.update": "管理员调整咨询师分配",
    "service_request.reject": "管理员关闭服务申请",
    "calendar_request.review": "管理员审核日历申请",
}

_RESOURCE_LABELS = {
    "user": "用户",
    "service_request": "服务申请",
    "calendar_request": "日历申请",
    "report": "报告",
    "calendar": "日历",
    "decision_log": "行动记录",
}


def _order_timestamp(value: datetime) -> float:
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return normalized.timestamp()


def build_admin_user_timeline(
    *,
    user_created_at,
    service_requests,
    calendar_requests,
    reports,
    report_tasks,
    calendars,
    decision_logs,
    audit_entries,
    limit: int = 30,
) -> list[dict]:
    events: list[dict] = []

    def add(key, event_type, label, occurred_at, resource_type, resource_id, description=""):
        if occurred_at is None:
            return
        events.append({
            "key": key,
            "event_type": event_type,
            "label": label,
            "description": description,
            "occurred_at": occurred_at,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id is not None else None,
        })

    add("user:created", "account", "用户注册", user_created_at, "user", None)

    for item in service_requests:
        request_type = item.service_type or "report"
        request_label = "日历服务申请" if request_type == "calendar" else "报告服务申请"
        direction = _CONSULTATION_LABELS.get(item.consultation_type)
        description = f"申请 #{item.id} · {request_label}"
        if direction:
            description += f" · {direction}"
        for field, label in _SERVICE_REQUEST_STAGES:
            add(
                f"service-request:{item.id}:{field}",
                "service_request",
                label,
                getattr(item, field, None),
                "service_request",
                item.id,
                description,
            )

    for item in calendar_requests:
        description = f"日历申请 #{item.id}"
        add(f"calendar-request:{item.id}:created", "calendar_request", "日历申请已提交", item.created_at,
            "calendar_request", item.id, description)
        add(f"calendar-request:{item.id}:reviewed", "calendar_request", "日历申请已审核", item.reviewed_at,
            "calendar_request", item.id, description)

    for item in reports:
        if item.is_deleted:
            continue
        description = f"{item.title or '用户报告'} #{item.id}"
        add(f"report:{item.id}:created", "report", "报告已生成", item.created_at,
            "report", item.id, description)
        add(f"report:{item.id}:reviewed", "report", "报告已审校", item.reviewed_at,
            "report", item.id, description)

    for item in report_tasks:
        label = {
            "processing": "报告任务处理中",
            "completed": "报告任务已完成",
            "failed": "报告任务失败",
        }.get(item.status, "报告任务状态更新")
        add(f"report-task:{item.task_id}", "report_task", label, item.updated_at or item.created_at,
            "report_task", item.task_id, f"报告任务 {item.task_id[:8]}")

    for item in calendars:
        description = f"日历 #{item.id} · 第 {item.version_number} 版"
        add(f"calendar:{item.id}:created", "calendar", "日历版本已创建", item.created_at,
            "calendar", item.id, description)
        add(f"calendar:{item.id}:published", "calendar", "日历版本已发布", item.published_at,
            "calendar", item.id, description)

    for item in decision_logs:
        label = "决策记录已保存" if item.kind == "decision" else "行动记录已保存"
        add(f"decision-log:{item.id}:created", "decision_log", label, item.created_at,
            "decision_log", item.id, f"记录 #{item.id} · {item.log_date}")

    for log, actor_name in audit_entries:
        label = _AUDIT_ACTION_LABELS.get(log.action, "后台操作")
        resource_label = _RESOURCE_LABELS.get(log.resource_type, "记录")
        description = f"{resource_label}{f' #{log.resource_id}' if log.resource_id else ''}"
        if actor_name:
            description += f" · 操作人：{actor_name}"
        add(f"audit:{log.id}", "audit", label, log.created_at,
            log.resource_type, log.resource_id, description)

    events.sort(key=lambda event: _order_timestamp(event["occurred_at"]), reverse=True)
    return events[:limit]
