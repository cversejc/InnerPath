"""Project and schedule practices from a delivered ReportVersion."""

from datetime import date


FREQUENCIES = {"daily", "weekly", "monthly", "quarterly"}
RESOURCE_ROLES = {"RESOURCE", "USEFUL_GOD", "STRUCTURE", "SELF_DIRECTION"}


def project_report_practices(semantics, report_version_id):
    findings = {
        row.get("finding_key"): row
        for row in (semantics or {}).get("findings", [])
        if isinstance(row, dict) and isinstance(row.get("finding_key"), str)
    }
    actions = []
    unavailable = []
    for key, finding in sorted(findings.items()):
        if str(finding.get("semantic_role", "")).upper() != "ACTION":
            continue
        data = finding.get("structured_data") or {}
        if not isinstance(data, dict):
            unavailable.append({"action_id": key, "reason": "报告中的行动缺少可排程条件"})
            continue
        path = data.get("reasoning_path") or {}
        if not isinstance(path, dict):
            path = {}
        frequency = data.get("frequency")
        duration = data.get("duration_minutes")
        steps = data.get("steps")
        required_text = (data.get("method"), data.get("observation"), data.get("stop_rule"))
        if (
            frequency not in FREQUENCIES
            or not isinstance(duration, int)
            or isinstance(duration, bool)
            or not 1 <= duration <= 60
            or not isinstance(steps, list)
            or not steps
            or any(not isinstance(step, str) or not step.strip() for step in steps)
            or any(not isinstance(value, str) or not value.strip() for value in required_text)
        ):
            unavailable.append({"action_id": key, "reason": "报告中的行动缺少可排程条件"})
            continue
        block_refs = data.get("block_refs") or []
        resource_refs = path.get("resource_refs") or []
        if (
            not isinstance(block_refs, list)
            or not block_refs
            or any(str(findings.get(ref, {}).get("semantic_role", "")).upper() != "BLOCK" for ref in block_refs)
            or not isinstance(resource_refs, list)
            or not resource_refs
            or any(not isinstance(ref, str) or ref not in findings
                   or str(findings[ref].get("semantic_role", "")).upper() not in RESOURCE_ROLES
                   for ref in resource_refs)
        ):
            unavailable.append({"action_id": key, "reason": "报告行动缺少有效的卡点或资源来源"})
            continue
        actions.append(
            {
                "action_id": key,
                "claim": finding.get("claim", ""),
                "frequency": frequency,
                "duration_minutes": duration,
                "steps": list(steps),
                "method": data["method"],
                "observation": data["observation"],
                "stop_rule": data["stop_rule"],
                "block_refs": list(block_refs),
                "resource_refs": list(resource_refs),
                "regulation_function": path.get("regulation_function", ""),
                "capacity": path.get("capacity", ""),
                "reality_gap": path.get("reality_gap", ""),
                "integration_task": path.get("integration_task", ""),
                "tool": path.get("tool", ""),
                "rationale": path.get("rationale", ""),
                "report_version_id": report_version_id,
            }
        )
    return {
        "version": 1,
        "report_version_id": report_version_id,
        "actions": actions,
        "unavailable_actions": unavailable,
    }


def plan_practice_schedule(practices, dates, available_minutes_per_day):
    if (
        not isinstance(available_minutes_per_day, int)
        or isinstance(available_minutes_per_day, bool)
        or not 5 <= available_minutes_per_day <= 480
    ):
        raise ValueError("calendar_available_time_invalid")
    if not isinstance(dates, list) or not dates or any(not isinstance(value, str) for value in dates):
        raise ValueError("calendar_practice_dates_invalid")
    if len(set(dates)) != len(dates):
        raise ValueError("calendar_practice_dates_invalid")
    days = [date.fromisoformat(value) for value in dates]
    if any(right <= left for left, right in zip(days, days[1:])):
        raise ValueError("calendar_practice_dates_invalid")

    schedule = {key: [] for key in dates}
    minutes = {key: 0 for key in dates}
    unavailable = []
    rank = {"daily": 0, "weekly": 1, "monthly": 2, "quarterly": 3}
    actions = sorted(
        (action for action in (practices or {}).get("actions", []) if isinstance(action, dict)),
        key=lambda item: (rank.get(item.get("frequency"), 4), item.get("duration_minutes", 0), item.get("action_id", "")),
    )
    for action in actions:
        key = action.get("action_id")
        duration = action.get("duration_minutes")
        frequency = action.get("frequency")
        if not isinstance(key, str) or frequency not in FREQUENCIES or not isinstance(duration, int) or isinstance(duration, bool) or duration < 1:
            unavailable.append({"action_id": key, "reason": "报告中的行动缺少可排程条件"})
            continue
        if duration > available_minutes_per_day:
            unavailable.append({"action_id": key, "reason": f"单次需 {duration} 分钟，超过每日预算 {available_minutes_per_day} 分钟"})
            continue

        if frequency == "daily":
            groups = [[key] for key in dates]
        elif frequency == "weekly":
            groups = [dates[index:index + 7] for index in range(0, len(dates), 7)]
        elif frequency == "monthly":
            groups = [dates]
        else:
            groups = [dates[max(0, len(dates) - 7):]]

        placements = []
        reserved_minutes = {}
        for group in groups:
            preferred_index = (len(group) - 1) // 2
            candidates = sorted(
                enumerate(group),
                key=lambda item: (
                    minutes[item[1]], abs(item[0] - preferred_index), item[0]
                ),
            )
            available_date = next(
                (day for _, day in candidates if minutes[day] + reserved_minutes.get(day, 0) + duration <= available_minutes_per_day),
                None,
            )
            if available_date is None:
                placements = []
                break
            placements.append(available_date)
            reserved_minutes[available_date] = reserved_minutes.get(available_date, 0) + duration
        if len(placements) != len(groups):
            unavailable.append({"action_id": key, "reason": "与其他报告练习叠加后超出每日可用时间"})
            continue
        for day in placements:
            minutes[day] += duration
            schedule[day].append(key)

    return schedule, unavailable


def validate_practice_entry(row, practices, available_minutes_per_day, scheduled_refs=None):
    actions = _practice_by_id(practices)
    refs = row.get("action_refs")
    if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
        raise ValueError("calendar_action_reference_invalid")
    if len(refs) != len(set(refs)) or any(ref not in actions for ref in refs):
        raise ValueError("calendar_action_reference_invalid")
    if scheduled_refs is not None and refs != scheduled_refs:
        raise ValueError("calendar_practice_schedule_mismatch")
    if any(actions[ref].get("duration_minutes", available_minutes_per_day + 1) > available_minutes_per_day for ref in refs):
        raise ValueError("calendar_practice_time_budget_exceeded")
    if sum(actions[ref]["duration_minutes"] for ref in refs) > available_minutes_per_day:
        raise ValueError("calendar_practice_time_budget_exceeded")


def validate_practice_schedule(entries, practices, available_minutes_per_day, scheduled_by_date):
    if not isinstance(entries, list) or not isinstance(scheduled_by_date, dict):
        raise ValueError("calendar_practice_schedule_mismatch")
    actions = _practice_by_id(practices)
    by_date = {row.get("entry_date"): row for row in entries if isinstance(row, dict)}
    if len(by_date) != len(entries) or set(by_date) != set(scheduled_by_date):
        raise ValueError("calendar_practice_schedule_mismatch")
    for day, row in by_date.items():
        validate_practice_entry(row, practices, available_minutes_per_day, scheduled_by_date[day])
    unknown = {ref for refs in scheduled_by_date.values() for ref in refs if ref not in actions}
    if unknown:
        raise ValueError("calendar_practice_schedule_mismatch")


def _practice_by_id(practices):
    return {
        action["action_id"]: action
        for action in (practices or {}).get("actions", [])
        if isinstance(action, dict) and isinstance(action.get("action_id"), str)
    }
