import pytest

from app.domains.calendar.practices import (
    plan_practice_schedule,
    project_report_practices,
    validate_practice_entry,
    validate_practice_schedule,
)


def action_finding(key, frequency="weekly", duration=15):
    return {
        "finding_key": key,
        "semantic_role": "ACTION",
        "claim": "练习边界沟通",
        "structured_data": {
            "frequency": frequency,
            "duration_minutes": duration,
            "steps": ["写下一句边界表达", "选择一次低风险沟通"],
            "method": "小步沟通",
            "observation": "记录对方实际回应",
            "stop_rule": "感到不安全时暂停并寻求支持",
            "block_refs": ["block.boundary"],
            "reasoning_path": {
                "resource_refs": ["resource.support"],
                "regulation_function": "降低准备成本",
                "capacity": "清晰表达",
                "reality_gap": "表达前容易反复准备",
                "integration_task": "兼顾关系与边界",
                "tool": "小步沟通",
                "rationale": "先在低风险情境检验",
            },
        },
    }


def test_report_action_projection_keeps_report_version_and_reasoning_sources():
    semantics = {"findings": [
        {"finding_key": "block.boundary", "semantic_role": "BLOCK"},
        {"finding_key": "resource.support", "semantic_role": "RESOURCE"},
        action_finding("action.boundary"),
    ]}

    projection = project_report_practices(semantics, 81)

    assert projection["report_version_id"] == 81
    assert projection["actions"] == [{
        "action_id": "action.boundary", "claim": "练习边界沟通", "frequency": "weekly",
        "duration_minutes": 15, "steps": ["写下一句边界表达", "选择一次低风险沟通"],
        "method": "小步沟通", "observation": "记录对方实际回应",
        "stop_rule": "感到不安全时暂停并寻求支持", "block_refs": ["block.boundary"],
        "resource_refs": ["resource.support"], "regulation_function": "降低准备成本",
        "capacity": "清晰表达", "reality_gap": "表达前容易反复准备",
        "integration_task": "兼顾关系与边界", "tool": "小步沟通",
        "rationale": "先在低风险情境检验", "report_version_id": 81,
    }]
    assert projection["unavailable_actions"] == []


def test_practice_schedule_enforces_time_budget_frequency_and_complete_coverage():
    practices = {"actions": [
        {"action_id": "action.daily", "frequency": "daily", "duration_minutes": 10},
        {"action_id": "action.weekly", "frequency": "weekly", "duration_minutes": 15},
        {"action_id": "action.monthly", "frequency": "monthly", "duration_minutes": 20},
    ]}
    dates = [f"2026-10-{day:02d}" for day in range(1, 31)]
    schedule, unavailable = plan_practice_schedule(practices, dates, 45)
    entries = [{"entry_date": day, "action_refs": schedule[day]} for day in dates]

    assert unavailable == []
    assert all("action.daily" in schedule[day] for day in dates)
    assert sum("action.weekly" in schedule[day] for day in dates) == 5
    assert sum("action.monthly" in schedule[day] for day in dates) == 1
    validate_practice_schedule(entries, practices, 45, schedule)

    with pytest.raises(ValueError, match="calendar_practice_time_budget_exceeded"):
        validate_practice_entry({"entry_date": "2026-10-01", "action_refs": [
            "action.daily", "action.weekly", "action.monthly"]}, practices, 30)

    too_little_time, unscheduled = plan_practice_schedule(practices, dates, 20)
    assert "action.monthly" in {item["action_id"] for item in unscheduled}
    assert all(sum({"action.daily": 10, "action.weekly": 15, "action.monthly": 20}[ref]
        for ref in refs) <= 20 for refs in too_little_time.values())

    with pytest.raises(ValueError, match="calendar_practice_schedule_mismatch"):
        validate_practice_schedule([{"entry_date": "2026-10-01", "action_refs": []}], practices, 45, schedule)


def test_projected_action_with_unreviewable_source_is_not_silently_schedulable():
    semantics = {"findings": [action_finding("action.boundary")]}

    projection = project_report_practices(semantics, 81)

    assert projection["actions"] == []
    assert projection["unavailable_actions"] == [{
        "action_id": "action.boundary", "reason": "报告行动缺少有效的卡点或资源来源"
    }]


def test_legacy_calendar_skill_output_is_compatible_without_action_refs():
    from app.domains.calendar.production import validate_daily

    window = {"period": "09:00–11:00", "label": "沟通", "suggestion": "安排短沟通"}
    recovery_window = {"period": "15:00–17:00", "label": "复盘", "suggestion": "留出反馈时间"}
    row = {
        "entry_date": "2026-10-01", "keyword": "边界、沟通",
        "summary": "今天先写下一个需要澄清的问题，再用轻量的方式确认事实并留下反馈空间。",
        "suitable": ["记录问题", "核对事实"], "energy_awareness": "我在担心什么？",
        "tone_explanation": "适合小步核对。", "windows": [window, recovery_window],
    }

    validate_daily(
        row, {"tone": "blue", "windows": [window, recovery_window]},
        {"day_pillar": "甲子", "windows": [window, recovery_window]},
        practice_rhythm={}, scheduled_refs=[], require_action_refs=False,
    )

    assert row["action_refs"] == []
