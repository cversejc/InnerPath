from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.service_request import SERVICE_REQUEST_STATUSES, SERVICE_REQUEST_TYPES
from app.services.service_request_service import (
    has_staff_assignment,
    normalize_calendar_draft,
    staff_can_access,
    validate_draft,
)


def make_calendar_payload(start_date: date):
    return {
        "title": "测试决策日历",
        "start_date": start_date.isoformat(),
        "end_date": (start_date + timedelta(days=29)).isoformat(),
        "meta_payload": {"rhythm": "先观察，再行动"},
        "entries": [
            {
                "entry_date": (start_date + timedelta(days=index)).isoformat(),
                "tone": "yellow",
                "status_label": "观察日",
                "keyword": f"关键词 {index + 1}",
                "summary": "先把信息理清，再决定下一步。",
                "suitable": ["整理计划"],
                "unsuitable": ["仓促拍板"],
            }
            for index in range(30)
        ],
    }


def test_service_request_domains_expose_all_workflow_states():
    assert SERVICE_REQUEST_TYPES == ("report", "calendar")
    assert SERVICE_REQUEST_STATUSES == (
        "submitted",
        "accepted",
        "ai_processing",
        "ai_ready",
        "reviewing",
        "needs_info",
        "failed",
        "delivered",
        "withdrawn",
        "rejected",
    )


def test_report_draft_requires_all_structured_sections():
    with pytest.raises(ValueError, match="report_draft_incomplete"):
        validate_draft("report", {"summary": "只有总结"})

    payload = {
        "energy_profile": {"type": "综合型"},
        "career_guidance": {"suitable_paths": ["研究型工作"]},
        "relationship_pattern": {"style": "边界清晰"},
        "personal_growth": {"action_plan": []},
        "summary": "这是一份经过审校的总结。",
    }
    assert validate_draft("report", payload)["title"] == "辰鉴·人生说明书"


def test_calendar_draft_rejects_duplicates_and_requires_full_thirty_days():
    start = date(2026, 9, 14)
    payload = make_calendar_payload(start)
    assert len(validate_draft("calendar", payload)["entries"]) == 30

    payload["entries"][-1]["entry_date"] = payload["entries"][0]["entry_date"]
    with pytest.raises(ValueError, match="duplicate_calendar_entry_date"):
        validate_draft("calendar", payload)

    incomplete = make_calendar_payload(start)
    incomplete["entries"] = incomplete["entries"][:-1]
    with pytest.raises(ValueError, match="calendar_entries_incomplete"):
        validate_draft("calendar", incomplete)


def test_calendar_window_is_always_taken_from_the_request_snapshot():
    start = date(2026, 9, 14)
    request = SimpleNamespace(
        request_payload={
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=29)).isoformat(),
        }
    )
    draft = normalize_calendar_draft(
        {"start_date": "2030-01-01", "end_date": "2030-01-30", "entries": []},
        request,
    )
    assert draft["start_date"] == start.isoformat()
    assert draft["end_date"] == (start + timedelta(days=29)).isoformat()


def test_consultant_access_is_assignment_scoped_but_admin_can_intervene():
    request = SimpleNamespace(assigned_consultant_id=12)
    assert staff_can_access(request, SimpleNamespace(role="consultant", id=12))
    assert not staff_can_access(request, SimpleNamespace(role="consultant", id=13))
    assert staff_can_access(request, SimpleNamespace(role="admin", id=99))


@pytest.mark.asyncio
async def test_user_access_assignment_uses_service_requests_only():
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: 41),
                SimpleNamespace(scalar_one_or_none=lambda: None),
            ]
        )
    )

    assert await has_staff_assignment(db, staff_id=12, user_id=55)
    assert not await has_staff_assignment(db, staff_id=13, user_id=55)

    for call in db.execute.await_args_list:
        statement = call.args[0]
        statement_text = str(statement)
        assert "service_requests.user_id" in statement_text
        assert "service_requests.assigned_consultant_id" in statement_text
        assert "service_requests.status NOT IN" in statement_text
