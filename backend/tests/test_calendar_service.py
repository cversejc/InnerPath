from datetime import date
from types import SimpleNamespace

import pytest

from app.schemas.calendar import CalendarRequestCreate
from app.services.calendar_service import create_calendar_request


def make_calendar_request_data() -> CalendarRequestCreate:
    return CalendarRequestCreate(
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 31),
        focus_topics=["career"],
        usage_scenario="before_decision",
        goal="确认下一步方向",
        expected_outcomes=["行动建议"],
    )


@pytest.mark.asyncio
async def test_incomplete_profile_cannot_create_calendar_request():
    user = SimpleNamespace(profile_completion=0)

    with pytest.raises(ValueError, match="calendar_request_profile_incomplete"):
        await create_calendar_request(None, user, make_calendar_request_data())
