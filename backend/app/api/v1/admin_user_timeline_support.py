from datetime import datetime, timezone

from app.domains.audit.service import parse_audit_details

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
    "workflow.step.assign": "调整报告流程负责人",
    "workflow.step.return": "退回报告流程节点",
    "workflow.step.reopen": "重新打开报告流程节点",
    "report_case.info_requested": "咨询师请求补充报告资料",
    "report_case.info_answered": "用户已补充报告资料",
    "report_case.deliver": "咨询师交付报告",
}

_STEP_STATUS_LABELS = {
    "WAITING_REVIEW": "等待复核",
    "IN_REVIEW": "人工复核中",
    "NEEDS_REVISION": "待修订",
    "FAILED": "处理失败",
    "CANCELLED": "已取消",
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
    report_cases=(),
    workflow_steps=(),
    workflow_audit_entries=(),
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

    case_by_workflow_id = {
        item.workflow_instance_id: item
        for item in report_cases
        if item.workflow_instance_id is not None
    }
    case_by_id = {item.id: item for item in report_cases}
    step_by_case_and_key = {}
    for case in report_cases:
        description = f"报告协作流程 #{case.id}"
        if case.service_request_id:
            description += f" · 申请 #{case.service_request_id}"
        add(
            f"report-case:{case.id}:created",
            "report_case",
            "报告协作流程已建立",
            case.created_at,
            "report_case",
            case.id,
            description,
        )

    for step in workflow_steps:
        case = case_by_workflow_id.get(step.workflow_instance_id)
        if case is None:
            continue
        step_by_case_and_key[(case.id, step.step_key)] = step
        step_description = (
            f"报告协作流程 #{case.id} · 第 {step.sequence_no} 步（{step.step_key}）"
        )
        if case.service_request_id:
            step_description += f" · 申请 #{case.service_request_id}"
        executor_label = {"HUMAN": "咨询师", "AI": "AI", "HYBRID": "协作"}.get(
            step.executor, "工作流"
        )
        step_events = (
            ("activated_at", f"报告第 {step.sequence_no} 步已开放"),
            ("started_at", f"{executor_label}开始处理报告第 {step.sequence_no} 步"),
            ("completed_at", f"报告第 {step.sequence_no} 步已完成"),
        )
        for field, label in step_events:
            add(
                f"report-step:{step.id}:{field}",
                "workflow_step",
                label,
                getattr(step, field, None),
                "report_case",
                case.id,
                step_description,
            )
        current_status_label = _STEP_STATUS_LABELS.get(step.status)
        if current_status_label:
            add(
                f"report-step:{step.id}:status:{step.status}",
                "workflow_step",
                f"报告第 {step.sequence_no} 步{current_status_label}",
                step.updated_at,
                "report_case",
                case.id,
                step_description,
            )

    for log, actor_name in workflow_audit_entries:
        label = _AUDIT_ACTION_LABELS.get(log.action)
        if not label:
            continue
        case_id = int(log.resource_id) if log.resource_id and log.resource_id.isdigit() else None
        case = case_by_id.get(case_id)
        details = parse_audit_details(log.details) or {}
        step_key = details.get("step_key")
        if not isinstance(step_key, str):
            step_key = None
        step = step_by_case_and_key.get((case_id, step_key))
        description = f"报告协作流程 #{case_id}" if case_id is not None else "报告协作流程"
        if case and case.service_request_id:
            description += f" · 申请 #{case.service_request_id}"
        if step:
            description += f" · 第 {step.sequence_no} 步（{step_key}）"
        elif step_key:
            description += f" · 节点 {step_key}"
        if actor_name:
            description += f" · 操作人：{actor_name}"
        add(
            f"workflow-audit:{log.id}",
            "workflow_action",
            label,
            log.created_at,
            "report_case",
            case_id or log.resource_id,
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
