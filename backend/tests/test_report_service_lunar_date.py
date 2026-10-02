from datetime import date, datetime
import pytest

from app.domains.reports.service import create_report, format_report_response


class FakeDatabase:
    def add(self, report):
        self.report = report

    async def commit(self):
        return None

    async def refresh(self, report):
        report.id = 7
        report.created_at = datetime(2026, 10, 2)


@pytest.mark.asyncio
async def test_report_stores_solar_date_but_returns_original_lunar_date():
    db = FakeDatabase()
    input_data = {
        "name": "林一",
        "gender": "female",
        "birth_year": 2023,
        "birth_month": 2,
        "birth_day": 1,
        "birth_is_leap_month": True,
        "calendar_type": "lunar",
    }

    report = await create_report(
        db,
        user_id=3,
        report_data={
            "basic_info": {"birth_date": "2023-02-01"},
            "energy_profile": {},
            "career_guidance": {},
            "relationship_pattern": {},
            "personal_growth": {},
        },
        generation_time_ms=15,
        input_data=input_data,
    )

    assert report.birth_date == date(2023, 3, 22)
    assert report.birth_calendar_type == "lunar"
    assert report.input_snapshot["birth_is_leap_month"] is True

    response = format_report_response(report)
    assert response["basic_info"]["birth_date"] == "2023-02-01"
    assert response["basic_info"]["solar_birth_date"] == "2023-03-22"
    assert response["basic_info"]["calendar_type"] == "lunar"
    assert response["basic_info"]["birth_is_leap_month"] is True
