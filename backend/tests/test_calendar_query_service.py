from datetime import date
from types import SimpleNamespace

import pytest

from app.domains.calendar.query_service import serialize_calendar


class CalendarDatabase:
    def __init__(self, entries):
        self.entries = entries

    async def execute(self, statement):
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(all=lambda: self.entries)
        )


@pytest.mark.asyncio
async def test_user_calendar_serialization_redacts_internal_notes():
    entry = SimpleNamespace(
        id=1,
        entry_date=date(2026, 10, 1),
        day_pillar="甲子",
        tone="green",
        status_label="适合推进",
        keyword="推进",
        summary="整理当前计划",
        suitable=["复盘"],
        unsuitable=[],
        time_window="上午",
        admin_note="仅供顾问查看",
    )
    calendar = SimpleNamespace(
        id=3,
        user_id=8,
        series_id="series",
        version_number=1,
        status="published",
        title="10月日历",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
        meta_payload={},
        calendar_request_id=None,
        published_at=None,
        created_at=None,
        updated_at=None,
    )

    response = await serialize_calendar(
        CalendarDatabase([entry]), calendar, include_internal=False
    )

    assert response["entries"][0]["admin_note"] is None
    assert response["entries"][0]["summary"] == "整理当前计划"
