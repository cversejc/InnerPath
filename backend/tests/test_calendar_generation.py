from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application import calendar_generation
from app.domains.calendar import service as calendar_service
from app.domains.calendar.generation import (
    build_calendar_prompt,
    validate_generated_calendar,
)
from app.domains.calendar.models import CalendarEntry
from app.domains.calendar.schemas import CalendarRequestCreate


def make_ai_calendar(start: date) -> dict:
    return {
        "title": "工作节奏决策日历",
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=29)).isoformat(),
        "meta_payload": {"intro": "以报告中的节奏建议为参照。"},
        "entries": [
            {
                "entry_date": (start + timedelta(days=index)).isoformat(),
                "tone": "yellow",
                "status_label": "观察与准备",
                "keyword": f"第 {index + 1} 天",
                "summary": "整理一个可验证的小步骤。",
                "suitable": ["记录当前判断依据"],
                "unsuitable": ["把一次结果当成长期结论"],
                "time_window": "按个人精力安排。",
                "admin_note": "",
            }
            for index in range(30)
        ],
    }


def test_calendar_prompt_contains_the_delivered_report_context():
    prompt = build_calendar_prompt(
        {
            "start_date": "2026-10-01",
            "end_date": "2026-10-30",
            "source_report": {"id": 7, "summary": "先内化理解，再小步验证。"},
        }
    )

    assert '"source_report"' in prompt
    assert "先内化理解，再小步验证" in prompt


def test_calendar_output_requires_all_thirty_dates_and_matching_range():
    start = date(2026, 10, 1)
    user_data = {
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=29)).isoformat(),
    }
    payload = make_ai_calendar(start)

    calendar = validate_generated_calendar(payload, user_data)

    assert calendar.start_date == start
    assert calendar.end_date == start + timedelta(days=29)
    assert len(calendar.entries) == 30

    with pytest.raises(ValueError, match="calendar_ai_incomplete_dates"):
        validate_generated_calendar({**payload, "entries": payload["entries"][:-1]}, user_data)

    duplicated = {**payload, "entries": list(payload["entries"])}
    duplicated["entries"][-1] = duplicated["entries"][0]
    with pytest.raises(ValueError, match="calendar_ai_incomplete_dates"):
        validate_generated_calendar(duplicated, user_data)


@pytest.mark.asyncio
async def test_report_calendar_generation_uses_report_and_automatically_delivers(monkeypatch):
    start = date(2026, 10, 1)
    request = SimpleNamespace(
        id=44,
        status="generating",
        user_id=36,
        source_report_id=7,
        start_date=start,
        end_date=start + timedelta(days=29),
        focus_topics=["career"],
        usage_scenario="before_decision",
        goal="找到一个可以开始验证的方向",
        decision_description=None,
        expected_outcomes=["daily_prompt"],
        additional_info=None,
        reviewer_id=None,
        input_snapshot={
            "profile": {"name": "演示用户"},
            "source_report": {"id": 7, "summary": "先内化理解，再小步验证。"},
        },
    )
    user_data_seen = {}

    async def create_request(*_args, **_kwargs):
        return request

    async def generate(user_data):
        user_data_seen.update(user_data)
        return make_ai_calendar(start)

    async def deliver(_db, *, calendar_request, **_kwargs):
        calendar_request.status = "fulfilled"

    monkeypatch.setattr(calendar_generation, "create_calendar_request", create_request)
    monkeypatch.setattr(calendar_generation, "generate_calendar_with_ai", generate)
    monkeypatch.setattr(calendar_generation, "create_ai_calendar_for_request", deliver)

    result = await calendar_generation.generate_calendar_from_report(
        SimpleNamespace(),
        SimpleNamespace(id=36),
        CalendarRequestCreate(
            profile_version=1,
            source_report_id=7,
            start_date=start,
            end_date=start + timedelta(days=29),
            focus_topics=["career"],
            usage_scenario="before_decision",
            goal="找到一个可以开始验证的方向",
            expected_outcomes=["daily_prompt"],
        ),
    )

    assert result.status == "fulfilled"
    assert user_data_seen["source_report"]["summary"] == "先内化理解，再小步验证。"
    assert result.reviewer_id is None


@pytest.mark.asyncio
async def test_ai_calendar_is_published_and_request_fulfilled_in_one_commit(monkeypatch):
    start = date(2026, 10, 1)
    request = SimpleNamespace(
        id=44,
        status="generating",
        source_report_id=7,
        input_snapshot={"generation": {"status": "RUNNING"}},
    )

    class FakeDatabase:
        def __init__(self):
            self.added = []
            self.commits = 0

        def add(self, value):
            self.added.append(value)
            if value.__class__.__name__ == "UserCalendar":
                value.id = 91

        async def flush(self):
            return None

        async def commit(self):
            self.commits += 1

        async def refresh(self, _value):
            return None

    db = FakeDatabase()
    monkeypatch.setattr(calendar_service, "record_audit", AsyncMock())
    calendar = await calendar_service.create_ai_calendar_for_request(
        db,
        calendar_request=request,
        user_id=36,
        created_by=36,
        data=validate_generated_calendar(
            make_ai_calendar(start),
            {
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=29)).isoformat(),
            },
        ),
    )

    entries = [item for item in db.added if isinstance(item, CalendarEntry)]
    assert calendar.id == 91
    assert calendar.status == "published"
    assert calendar.calendar_request_id == request.id
    assert len(entries) == 30
    assert request.status == "fulfilled"
    assert request.input_snapshot["generation"]["status"] == "COMPLETED"
    assert db.commits == 1
